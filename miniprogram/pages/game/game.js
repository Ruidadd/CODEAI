const E = require('../../engine/civ-engine.js');
const save = require('../../utils/save.js');

const TABS = [{ id: 'build', name: '建造' }, { id: 'tech', name: '科技' }, { id: 'wonder', name: '奇观' }, { id: 'log', name: '动态' }];
const MEDALS = ['🥇', '🥈', '🥉', '4'];

function toast(text, ok) {
  wx.showToast({ title: text, icon: 'none', duration: ok ? 1200 : 2200 });
}
function buzz() { try { wx.vibrateShort({ type: 'light' }); } catch (e) { /* ignore */ } }

function toCard(c, type) {
  let tag = '', tagCls = '';
  if (type === 'research' && !c.repeat) { tag = c.state === 'done' ? '已完成' : c.eraName; tagCls = c.state === 'done' ? '' : 'era'; }
  else if (c.state === 'locked' || c.state === 'taken') tag = c.lockText;
  else if (c.state === 'done') tag = c.repeat ? '可重复' : '已完成';
  else if (c.repeat) tag = '可重复';
  return { id: c.id, type, state: c.state, icon: c.icon, name: c.name, effect: c.effect, tag, tagCls, pill: c.state === 'done' && !c.repeat ? '✓' : c.costText };
}

Page({
  data: { view: null, tab: 'build', tabs: TABS, cards: [], cardHead: '', resRows: [], pips: [], canEnd: false, modal: null },
  game: null,
  seenTurn: 0,

  onLoad() {
    const game = save.loadGame();
    if (!game) { wx.reLaunch({ url: '/pages/index/index' }); return; }
    this.game = game;
    const meta = save.getMeta();
    this.seenTurn = meta.seenTurn || 0;
    this.setData({ tab: meta.tab || 'build' });
    this.refresh();
    if (meta.fresh && !save.get('help-seen')) { save.set('help-seen', '1'); this.showHelp(true); }
    else this.queueModals();
    if (meta.fresh) save.setMeta({ seenTurn: this.seenTurn, tab: this.data.tab });
  },
  onShareAppMessage() {
    const v = this.game ? E.getView(this.game) : null;
    const me = v ? v.players.filter(p => p.isHuman)[0] : null;
    return { title: me ? '我在文明小桌用' + me.civName + '拿了 ' + me.score + ' 分，来挑战今天的地图吧' : '文明小桌：一局二十回合的桌游版文明', path: '/pages/index/index' };
  },

  persist() { save.saveGame(this.game); save.setMeta({ seenTurn: this.seenTurn, tab: this.data.tab }); },
  afterChange() { this.persist(); this.refresh(); this.queueModals(); },

  refresh() {
    const v = E.getView(this.game);
    const r = v.me.res, inc = v.me.income;
    const resRows = [
      { k: 'F', label: '🌾 粮食', val: r.F, inc: inc.F }, { k: 'P', label: '⚒️ 生产', val: r.P, inc: inc.P },
      { k: 'S', label: '🔬 科技', val: r.S, inc: inc.S }, { k: 'C', label: '🎭 文化', val: r.C, inc: inc.C }
    ];
    const pips = [];
    for (let i = 0; i < v.actionsPerTurn; i++) pips.push(i < v.actionsLeft);
    this.setData({ view: v, resRows, pips, canEnd: v.phase === 'playing' && v.isHumanTurn, ...this.cardsFor(v, this.data.tab) });
  },
  cardsFor(v, tab) {
    if (tab === 'build') return { cards: v.buildings.map(b => toCard(b, b.id === 'festival' ? 'festival' : 'build')), cardHead: '' };
    if (tab === 'tech') return { cards: v.techs.map(t => toCard(t, t.id === 'future' ? 'future' : 'research')), cardHead: '研究完本时代的 ' + v.me.techsPerEra + ' 项科技就进入下一时代 · 当前 ' + v.me.eraName };
    if (tab === 'wonder') return { cards: v.wonders.map(w => toCard(w, 'wonder')), cardHead: '奇观全场唯一，谁先建成归谁 · 每座 +' + E.SCORE.wonder + ' 分' };
    return { cards: [], cardHead: '' };
  },

  onTab(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ tab, ...this.cardsFor(this.data.view, tab) });
    save.setMeta({ seenTurn: this.seenTurn, tab });
  },
  onTile(e) {
    if (!this.game || this.game.phase !== 'playing') return;
    const idx = Number(e.currentTarget.dataset.idx);
    const v = this.data.view, t = v.board.tiles[idx];
    if (t.claimable) {
      const r = E.applyAction(this.game, { type: 'expand', idx });
      if (r.ok) { buzz(); toast(v.me.icon + ' ' + r.msg, true); this.afterChange(); } else toast(r.msg);
      return;
    }
    const info = E.tileInfo(this.game, idx);
    toast(info.icon + ' ' + info.title + (info.lines.length ? '，' + info.lines.join('，') : ''));
  },
  onCard(e) {
    if (!this.game || this.game.phase !== 'playing' || !this.data.view.isHumanTurn) return;
    const { type, id } = e.currentTarget.dataset;
    const r = E.applyAction(this.game, { type, id });
    if (r.ok) { buzz(); toast(this.data.view.me.icon + ' ' + r.msg, true); this.afterChange(); } else toast(r.msg);
  },
  onEnd() {
    if (!this.game || this.game.phase !== 'playing' || !this.data.view.isHumanTurn) return;
    const hasAI = this.data.view.players.some(p => !p.isHuman);
    if (hasAI) {
      this.setData({ modal: { type: 'busy', title: '⏳ 其他文明行动中…', center: true, buttons: [] } });
      setTimeout(() => { E.endTurn(this.game); this.setData({ modal: null }); this.afterChange(); }, 450);
    } else {
      E.endTurn(this.game); this.afterChange();
    }
  },

  // ---------- 弹层 ----------
  queueModals() {
    const v = this.data.view;
    if (v.phase === 'over') { this.showOver(v); return; }
    if (v.humanCount > 1 && v.isHumanTurn && v.turnNo !== this.seenTurn) { this.showHandoff(v); return; }
    this.seenTurn = v.turnNo; this.persist();
    if (v.pendingEvent) this.showEvent(v.pendingEvent);
  },
  showEvent(ev) {
    this.setData({ modal: { type: 'event', center: true, icon: ev.icon, title: '事件 · ' + ev.name, text: ev.text, buttons: [{ id: 'event-ok', label: '知道了', cls: 'primary big' }] } });
  },
  showHandoff(v) {
    this.setData({ modal: { type: 'handoff', center: true, icon: v.me.icon, title: '轮到 ' + v.me.name, text: v.me.civName + ' · ' + v.me.bonus + '\n请把手机交给 TA，其他人先别偷看。', buttons: [{ id: 'handoff-ok', label: '我准备好了', cls: 'primary big' }] } });
  },
  showOver(v) {
    let myIdx = -1;
    v.ranking.forEach((p, i) => { if (p.isHuman && myIdx < 0) myIdx = i; });
    if (v.mode === 'daily' && v.humanCount === 1 && myIdx >= 0) {
      const me = v.ranking[myIdx], key = 'best/' + v.seed;
      let prev = null;
      try { prev = JSON.parse(save.get(key) || 'null'); } catch (e) { prev = null; }
      if (!prev || me.score > prev.score) save.set(key, JSON.stringify({ score: me.score, rank: myIdx + 1, civ: me.civName }));
    }
    const top = v.ranking[0];
    this.setData({ modal: {
      type: 'over', title: top.isHuman ? '🎉 ' + top.name + ' 赢了' : '时代落幕',
      text: v.maxRound + ' 回合过去，' + top.name + ' 以 ' + top.score + ' 分成为最伟大的文明。',
      ranking: v.ranking, medals: MEDALS,
      buttons: [{ id: 'again', label: '再来一局', cls: 'primary big' }, { id: 'share', label: '分享战报', cls: '' }, { id: 'home', label: '回到首页', cls: 'ghost' }]
    } });
  },
  showHelp(first) {
    this.setData({ modal: {
      type: 'help', title: '玩法说明',
      lines: [
        { b: '扩张：', t: '🌾粮食用来占领土地。点击发亮的格子即可，领土越多越贵。' },
        { b: '建造：', t: '⚒️生产用来建建筑和奇观。建筑每回合带来产出；奇观全场唯一，谁先建成归谁。' },
        { b: '研究：', t: '🔬科技用来研究。研究完本时代的 3 项科技就进入下一时代，解锁新东西。' },
        { b: '行动：', t: '每回合最多 ' + E.ACTIONS_PER_TURN + ' 次行动，做完点「结束回合」。每 3 回合翻开一张事件卡，影响所有文明。' },
        { b: '胜负：', t: E.MAX_ROUND + ' 回合后分数最高者获胜。分数 = 领土×' + E.SCORE.tile + ' + 建筑×' + E.SCORE.building + ' + 科技×' + E.SCORE.tech + ' + 奇观×' + E.SCORE.wonder + ' + 🎭文化。' }
      ],
      civs: E.CIVS, first: !!first,
      buttons: [{ id: 'help-ok', label: first ? '开始吧' : '知道了', cls: 'primary big' }]
    } });
  },
  showMenu() {
    this.setData({ modal: { type: 'menu', title: '菜单', buttons: [
      { id: 'help', label: '玩法说明', cls: '' }, { id: 'home', label: '保存并回到首页', cls: '' },
      { id: 'restart', label: '放弃本局，回首页重开', cls: 'danger' }, { id: 'close', label: '继续游戏', cls: 'ghost' }
    ] } });
  },
  onMenu() { this.showMenu(); },
  onModalBg() {
    const m = this.data.modal;
    if (m && (m.type === 'menu' || m.type === 'help')) this.closeModal();
  },
  closeModal() { this.setData({ modal: null }); },
  noop() {},
  onModalBtn(e) {
    const id = e.currentTarget.dataset.id, m = this.data.modal;
    switch (id) {
      case 'event-ok': E.ackEvent(this.game); this.closeModal(); this.persist(); this.refresh(); break;
      case 'handoff-ok': this.seenTurn = this.data.view.turnNo; this.closeModal(); this.persist(); this.queueModals(); break;
      case 'help-ok': { const first = m && m.first; this.closeModal(); if (first) this.queueModals(); break; }
      case 'help': this.showHelp(false); break;
      case 'close': this.closeModal(); break;
      case 'home': this.closeModal(); this.persist(); wx.navigateBack(); break;
      case 'restart': this.closeModal(); save.clearGame(); wx.navigateBack(); break;
      case 'again': this.closeModal(); this.restartSame(); break;
      case 'share': toast('点右上角「…」可以分享给好友'); break;
      default: this.closeModal();
    }
  },
  restartSame() {
    const g = this.game;
    const players = g.players.map((p, i) => ({ civ: i === 0 ? p.civ : null, isHuman: p.isHuman, name: p.isHuman && g.players.filter(x => x.isHuman).length > 1 ? p.name : undefined }));
    const seed = g.mode === 'daily' ? E.dailySeed(new Date()) : (Date.now() % 2147483647);
    this.game = E.createGame({ seed, mode: g.mode, difficulty: g.difficulty, players });
    this.seenTurn = 0;
    this.setData({ tab: 'build' });
    this.afterChange();
  }
});
