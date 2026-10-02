const E = require('../../engine/civ-engine.js');
const save = require('../../utils/save.js');

const MODES = [{ id: 'daily', name: '每日一局' }, { id: 'random', name: '随机地图' }, { id: 'hotseat', name: '多人同机' }];
const MODE_NOTE = {
  daily: '今天所有人玩的都是同一张地图，比比谁的分高。',
  random: '每次都是一张新地图。',
  hotseat: '两到四位朋友共用一台手机，轮到谁就递给谁。'
};
const DIFFS = [{ id: 'easy', name: '轻松' }, { id: 'normal', name: '普通' }, { id: 'hard', name: '困难' }];

function helpLines() {
  return [
    { b: '扩张：', t: '🌾粮食用来占领土地。点击发亮的格子即可，领土越多越贵。' },
    { b: '建造：', t: '⚒️生产用来建建筑和奇观。建筑每回合带来产出；奇观全场唯一，谁先建成归谁。' },
    { b: '研究：', t: '🔬科技用来研究。研究完本时代的 3 项科技就进入下一时代，解锁新东西。' },
    { b: '行动：', t: '每回合最多 ' + E.ACTIONS_PER_TURN + ' 次行动，做完点「结束回合」。每 3 回合翻开一张事件卡，影响所有文明。' },
    { b: '胜负：', t: E.MAX_ROUND + ' 回合后分数最高者获胜。分数 = 领土×' + E.SCORE.tile + ' + 建筑×' + E.SCORE.building + ' + 科技×' + E.SCORE.tech + ' + 奇观×' + E.SCORE.wonder + ' + 🎭文化。' }
  ];
}

Page({
  data: {
    modes: MODES, diffs: DIFFS, civs: E.CIVS,
    mode: 'daily', modeNote: MODE_NOTE.daily, civ: 'china', opp: 2, diff: 'normal', humans: 2,
    hasSave: false, bestLine: '', help: false, helpLines: helpLines()
  },
  onShow() {
    const saved = save.loadGame();
    let bestLine = '';
    const best = save.get('best/' + E.dailySeed(new Date()));
    if (best) { try { const b = JSON.parse(best); bestLine = '今日最佳：' + b.score + ' 分（第 ' + b.rank + ' 名，' + b.civ + '）'; } catch (e) { /* ignore */ } }
    this.setData({ hasSave: !!(saved && saved.phase === 'playing'), bestLine });
  },
  pickMode(e) { const mode = e.currentTarget.dataset.v; this.setData({ mode, modeNote: MODE_NOTE[mode] }); },
  pickCiv(e) { this.setData({ civ: e.currentTarget.dataset.v }); },
  pickOpp(e) { this.setData({ opp: Number(e.currentTarget.dataset.v) }); },
  pickDiff(e) { this.setData({ diff: e.currentTarget.dataset.v }); },
  pickHumans(e) { this.setData({ humans: Number(e.currentTarget.dataset.v) }); },
  showHelp() { this.setData({ help: true }); },
  closeHelp() { this.setData({ help: false }); },
  noop() {},

  start() {
    const d = this.data, players = [];
    if (d.mode === 'hotseat') {
      for (let i = 0; i < d.humans; i++) players.push({ civ: i === 0 ? d.civ : null, isHuman: true, name: '玩家' + (i + 1) });
    } else {
      players.push({ civ: d.civ, isHuman: true });
      for (let i = 0; i < d.opp; i++) players.push({ civ: null, isHuman: false });
    }
    const seed = d.mode === 'daily' ? E.dailySeed(new Date()) : (Date.now() % 2147483647);
    const game = E.createGame({ seed, mode: d.mode, difficulty: d.diff, players });
    save.saveGame(game);
    save.setMeta({ seenTurn: 0, tab: 'build', fresh: true });
    wx.navigateTo({ url: '/pages/game/game' });
  },
  continueGame() { wx.navigateTo({ url: '/pages/game/game' }); },
  onShareAppMessage() { return { title: '文明小桌：一局二十回合的桌游版文明', path: '/pages/index/index' }; }
});
