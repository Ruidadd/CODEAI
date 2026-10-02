/* 文明小桌 · 网页版交互（同一引擎，渲染引擎给出的视图模型） */
(function () {
  'use strict';
  var E = window.CivEngine;
  var $ = function (s) { return document.querySelector(s); };
  var SAVE_KEY = 'civ-board/save', META_KEY = 'civ-board/meta', BEST_KEY = 'civ-board/best/', HELP_KEY = 'civ-board/help-seen';
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 隐私模式等情况下忽略 */ } },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) { /* ignore */ } }
  };
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  var game = null, tab = 'build', seenTurn = 0, toastTimer = null;
  var setup = { mode: 'daily', civ: 'china', opp: 2, diff: 'normal', humans: 2 };
  var MODE_NOTE = {
    daily: '今天所有人玩的都是同一张地图，比比谁的分高。',
    random: '每次都是一张新地图。',
    hotseat: '两到四位朋友共用一台手机，轮到谁就递给谁。'
  };

  // ------------------------------------------------------------ 开始页
  function initStart() {
    var grid = $('#civGrid');
    grid.innerHTML = E.CIVS.map(function (c) {
      return '<button type="button" class="civ' + (c.id === setup.civ ? ' is-on' : '') + '" data-civ="' + c.id + '" style="--civ:' + c.color + '">' +
        '<span class="ci">' + c.icon + '</span><span class="cn">' + c.name + '</span><span class="cb">' + esc(c.bonus) + '</span></button>';
    }).join('');
    grid.addEventListener('click', function (e) {
      var b = e.target.closest('.civ'); if (!b) return;
      setup.civ = b.getAttribute('data-civ');
      grid.querySelectorAll('.civ').forEach(function (x) { x.classList.toggle('is-on', x === b); });
    });
    bindSeg('#modeSeg', 'mode', function () {
      $('#modeNote').textContent = MODE_NOTE[setup.mode];
      $('#oppPanel').hidden = setup.mode === 'hotseat';
      $('#hotPanel').hidden = setup.mode !== 'hotseat';
    });
    bindSeg('#oppSeg', 'opp', null, Number);
    bindSeg('#diffSeg', 'diff');
    bindSeg('#humanSeg', 'humans', null, Number);
    $('#btnStart').addEventListener('click', startGame);
    $('#btnContinue').addEventListener('click', continueGame);
    $('#btnHelp').addEventListener('click', function () { showHelp(false); });
    refreshStart();
  }
  function bindSeg(sel, key, after, cast) {
    var seg = $(sel);
    seg.addEventListener('click', function (e) {
      var b = e.target.closest('.seg-btn'); if (!b) return;
      setup[key] = cast ? cast(b.getAttribute('data-v')) : b.getAttribute('data-v');
      seg.querySelectorAll('.seg-btn').forEach(function (x) { x.classList.toggle('is-on', x === b); });
      if (after) after();
    });
  }
  function refreshStart() {
    var saved = loadSaved();
    $('#btnContinue').hidden = !(saved && saved.phase === 'playing');
    var best = store.get(BEST_KEY + E.dailySeed(new Date()));
    var line = '';
    if (best) { try { var b = JSON.parse(best); line = '今日最佳：' + b.score + ' 分（第 ' + b.rank + ' 名，' + b.civ + '）'; } catch (e) { /* ignore */ } }
    $('#bestLine').textContent = line;
  }
  function loadSaved() {
    var s = store.get(SAVE_KEY); if (!s) return null;
    try { return E.load(s); } catch (e) { return null; }
  }
  function startGame() {
    var players = [], i;
    if (setup.mode === 'hotseat') {
      for (i = 0; i < setup.humans; i++) players.push({ civ: i === 0 ? setup.civ : null, isHuman: true, name: '玩家' + (i + 1) });
    } else {
      players.push({ civ: setup.civ, isHuman: true });
      for (i = 0; i < setup.opp; i++) players.push({ civ: null, isHuman: false });
    }
    var seed = setup.mode === 'daily' ? E.dailySeed(new Date()) : (Date.now() % 2147483647);
    game = E.createGame({ seed: seed, mode: setup.mode, difficulty: setup.diff, players: players });
    seenTurn = 0; tab = 'build';
    setTab('build');
    showScreen('game');
    afterChange();
    if (!store.get(HELP_KEY)) { showHelp(true); store.set(HELP_KEY, '1'); }
  }
  function continueGame() {
    var g = loadSaved(); if (!g) return;
    game = g;
    try { var meta = JSON.parse(store.get(META_KEY) || '{}'); seenTurn = meta.seenTurn || 0; tab = meta.tab || 'build'; } catch (e) { seenTurn = 0; }
    setTab(tab);
    showScreen('game');
    afterChange();
  }
  function showScreen(name) {
    $('#start').hidden = name !== 'start';
    $('#game').hidden = name !== 'game';
    window.scrollTo(0, 0);
    if (name === 'start') refreshStart();
  }

  // ------------------------------------------------------------ 对局页
  function save() {
    if (!game) return;
    store.set(SAVE_KEY, E.serialize(game));
    store.set(META_KEY, JSON.stringify({ seenTurn: seenTurn, tab: tab }));
  }
  function afterChange() { save(); render(); queueModals(); }

  function render() {
    var v = E.getView(game);
    $('#roundText').textContent = '第 ' + v.round + ' / ' + v.maxRound + ' 回合';
    $('#eraText').textContent = v.me.icon + ' ' + v.me.name + ' · ' + v.me.eraName;
    $('#playersStrip').innerHTML = v.players.map(function (p) {
      return '<span class="pchip' + (p.isCur ? ' is-cur' : '') + '" style="--c:' + p.color + '"><span class="dot"></span>' + p.icon + ' ' + esc(p.name) + ' <span class="sc">' + p.score + '</span></span>';
    }).join('');
    var inc = v.me.income, res = v.me.res;
    $('#meBar').innerHTML = [['F', '🌾 粮食', res.F, inc.F], ['P', '⚒️ 生产', res.P, inc.P], ['S', '🔬 科技', res.S, inc.S], ['C', '🎭 文化', res.C, inc.C]].map(function (r) {
      return '<div class="res" title="' + E.RES[r[0]].use + '"><span class="rn"><span>' + r[1] + '</span></span><span class="rv">' + r[2] + '<span class="ri">+' + r[3] + '</span></span></div>';
    }).join('');
    $('#board').innerHTML = v.board.tiles.map(function (t) {
      var cls = 'tile t-' + t.terrain + (t.owner >= 0 ? ' owned' : '') + (t.isCap ? ' cap' : '') + (t.claimable ? ' claimable' : '') + (t.affordable ? ' affordable' : '');
      var style = t.owner >= 0 ? ' style="--owner:' + t.color + '"' : '';
      return '<button type="button" class="' + cls + '" data-idx="' + t.idx + '"' + style + ' aria-label="' + esc(t.name) + '">' +
        '<span class="ti">' + t.icon + '</span>' + (t.claimable ? '<span class="cost">' + t.cost + '</span>' : '') + '</button>';
    }).join('');
    $('#hint').textContent = v.hint;
    renderCards(v);
    var pips = '';
    for (var i = 0; i < v.actionsPerTurn; i++) pips += '<span class="pip' + (i < v.actionsLeft ? '' : ' off') + '"></span>';
    $('#actionsLeft').innerHTML = v.phase === 'playing' ? '<span>行动</span>' + pips : '';
    $('#btnEnd').disabled = !(v.phase === 'playing' && v.isHumanTurn);
    $('#btnEnd').textContent = v.phase === 'over' ? '对局结束' : '结束回合';
  }

  function renderCards(v) {
    var html = '';
    function card(c, type) {
      var extra = '';
      if (type === 'research' && !c.repeat) extra = c.state === 'done' ? '<span class="tag">已完成</span>' : '<span class="tag era">' + esc(c.eraName) + '</span>';
      else if (c.state === 'locked' || c.state === 'taken') extra = '<span class="tag">' + esc(c.lockText) + '</span>';
      else if (c.state === 'done') extra = '<span class="tag">' + (c.repeat ? '可重复' : '已完成') + '</span>';
      else if (c.repeat) extra = '<span class="tag">可重复</span>';
      return '<button type="button" class="card ' + c.state + '" data-type="' + type + '" data-id="' + c.id + '">' +
        '<span class="ic">' + c.icon + '</span><span><span class="nm">' + esc(c.name) + extra + '</span><span class="ef">' + esc(c.effect) + '</span></span>' +
        '<span class="pill">' + (c.state === 'done' && !c.repeat ? '✓' : esc(c.costText)) + '</span></button>';
    }
    if (tab === 'build') {
      html = v.buildings.map(function (b) { return card(b, b.id === 'festival' ? 'festival' : 'build'); }).join('');
    } else if (tab === 'tech') {
      html = '<p class="card-head">研究完本时代的 ' + v.me.techsPerEra + ' 项科技就进入下一时代 · 当前 ' + esc(v.me.eraName) + '</p>' +
        v.techs.map(function (t) { return card(t, t.id === 'future' ? 'future' : 'research'); }).join('');
    } else if (tab === 'wonder') {
      html = '<p class="card-head">奇观全场唯一，谁先建成归谁 · 每座 +' + E.SCORE.wonder + ' 分</p>' +
        v.wonders.map(function (w) { return card(w, 'wonder'); }).join('');
    } else {
      html = v.log.length ? v.log.map(function (l) {
        return '<div class="logrow' + (l.isMe ? ' me' : '') + '" style="--lc:' + (l.color || 'inherit') + '"><span>' + l.icon + '</span><span><span class="lr">第 ' + l.round + ' 回合</span> ' +
          (l.who ? '<span class="lw">' + esc(l.who) + '</span> ' : '') + esc(l.text) + '</span></div>';
      }).join('') : '<p class="note center">还没有动静</p>';
    }
    $('#cards').innerHTML = html;
  }

  function setTab(name) {
    tab = name;
    document.querySelectorAll('#tabs button').forEach(function (b) { b.classList.toggle('is-on', b.getAttribute('data-tab') === name); });
    if (game) { renderCards(E.getView(game)); save(); }
  }

  function onTile(idx) {
    if (!game || game.phase !== 'playing') return;
    var v = E.getView(game), t = v.board.tiles[idx];
    if (t.claimable) {
      var r = E.applyAction(game, { type: 'expand', idx: idx });
      if (r.ok) { toast(v.me.icon + ' ' + r.msg, true); afterChange(); } else { toast(r.msg); }
      return;
    }
    var info = E.tileInfo(game, idx);
    toast(info.icon + ' ' + info.title + (info.lines.length ? ' · ' + info.lines.join('，') : ''));
  }

  function onCard(type, id) {
    if (!game || game.phase !== 'playing') return;
    var v = E.getView(game);
    if (!v.isHumanTurn) return;
    var r = E.applyAction(game, { type: type, id: id });
    if (r.ok) { toast(v.me.icon + ' ' + r.msg, true); afterChange(); } else { toast(r.msg); }
  }

  function endTurn() {
    if (!game || game.phase !== 'playing') return;
    var v = E.getView(game);
    if (!v.isHumanTurn) return;
    var hasAI = v.players.some(function (p) { return !p.isHuman; });
    if (hasAI) {
      showModal('<div class="busy">⏳ 其他文明行动中…</div>', true);
      setTimeout(function () { E.endTurn(game); closeModal(); afterChange(); }, 450);
    } else {
      E.endTurn(game); afterChange();
    }
  }

  // ------------------------------------------------------------ 弹层
  function queueModals() {
    var v = E.getView(game);
    if (v.phase === 'over') { showOver(v); return; }
    if (v.humanCount > 1 && v.isHumanTurn && v.turnNo !== seenTurn) { showHandoff(v); return; }
    seenTurn = v.turnNo; save();
    if (v.pendingEvent) { showEvent(v.pendingEvent); }
  }
  function showModal(html, plain) {
    var card = $('#modalCard');
    card.className = 'modal-card' + (plain ? ' center' : '');
    card.innerHTML = html;
    $('#modal').hidden = false;
  }
  function closeModal() { $('#modal').hidden = true; }
  function showEvent(ev) {
    showModal('<div class="m-icon">' + ev.icon + '</div><h2>事件 · ' + esc(ev.name) + '</h2><p class="m-text">' + esc(ev.text) + '</p>' +
      '<div class="m-actions"><button type="button" class="btn primary big" id="mOk">知道了</button></div>', true);
    $('#mOk').addEventListener('click', function () { E.ackEvent(game); closeModal(); save(); render(); });
  }
  function showHandoff(v) {
    showModal('<div class="m-icon">' + v.me.icon + '</div><h2>轮到 ' + esc(v.me.name) + '</h2><p class="m-text">' + esc(v.me.civName) + ' · ' + esc(v.me.bonus) + '<br>请把手机交给 TA，其他人先别偷看。</p>' +
      '<div class="m-actions"><button type="button" class="btn primary big" id="mOk">我准备好了</button></div>', true);
    $('#mOk').addEventListener('click', function () { seenTurn = v.turnNo; closeModal(); save(); queueModals(); });
  }
  function showOver(v) {
    var medals = ['🥇', '🥈', '🥉', '4'];
    var myIdx = -1;
    v.ranking.forEach(function (p, i) { if (p.isHuman && myIdx < 0) myIdx = i; });
    if (v.mode === 'daily' && v.humanCount === 1) {
      var me = v.ranking[myIdx];
      var key = BEST_KEY + v.seed, prev = null;
      try { prev = JSON.parse(store.get(key) || 'null'); } catch (e) { prev = null; }
      if (!prev || me.score > prev.score) store.set(key, JSON.stringify({ score: me.score, rank: myIdx + 1, civ: me.civName }));
    }
    var rows = v.ranking.map(function (p, i) {
      return '<div class="rrow' + (i === 0 ? ' win' : '') + '" style="--c:' + p.color + '"><span>' + medals[i] + '</span><span>' + p.icon + ' ' + esc(p.name) +
        '<div class="rd">领土 ' + p.tiles + ' · 科技 ' + p.techs + ' · 建筑 ' + p.buildings + ' · 奇观 ' + p.wonders.length + '</div></span><span class="rs">' + p.score + '</span></div>';
    }).join('');
    var title = v.ranking[0].isHuman ? '🎉 ' + esc(v.ranking[0].name) + ' 赢了' : '时代落幕';
    showModal('<h2>' + title + '</h2><p class="m-text">' + v.maxRound + ' 回合过去，' + esc(v.ranking[0].name) + ' 以 ' + v.ranking[0].score + ' 分成为最伟大的文明。</p><div class="rank">' + rows + '</div>' +
      '<div class="m-actions"><button type="button" class="btn primary big" id="mAgain">再来一局</button><button type="button" class="btn" id="mCopy">复制战报</button><button type="button" class="btn ghost" id="mHome">回到首页</button></div>');
    $('#mAgain').addEventListener('click', function () { closeModal(); store.del(SAVE_KEY); startGame(); });
    $('#mHome').addEventListener('click', function () { closeModal(); store.del(SAVE_KEY); showScreen('start'); });
    $('#mCopy').addEventListener('click', function () {
      var text = '文明小桌 · ' + (v.mode === 'daily' ? '每日一局 ' + v.seed : '随机地图') + '\n' + v.ranking.map(function (p, i) { return medals[i] + ' ' + p.name + ' ' + p.score + '分'; }).join('\n');
      copyText(text, this);
    });
  }
  function showHelp(first) {
    showModal('<h2>玩法说明</h2><div class="help"><ol>' +
      '<li><b>扩张</b>：🌾粮食用来占领土地。点击发亮的格子即可，领土越多越贵。</li>' +
      '<li><b>建造</b>：⚒️生产用来建建筑和奇观。建筑每回合带来产出；奇观全场唯一，谁先建成归谁。</li>' +
      '<li><b>研究</b>：🔬科技用来研究。研究完本时代的 3 项科技就进入下一时代，解锁新东西。</li>' +
      '<li><b>行动</b>：每回合最多 ' + E.ACTIONS_PER_TURN + ' 次行动，做完点「结束回合」。每 3 回合翻开一张事件卡，影响所有文明。</li>' +
      '<li><b>胜负</b>：' + E.MAX_ROUND + ' 回合后分数最高者获胜。分数 = 领土×' + E.SCORE.tile + ' + 建筑×' + E.SCORE.building + ' + 科技×' + E.SCORE.tech + ' + 奇观×' + E.SCORE.wonder + ' + 🎭文化。</li>' +
      '</ol><p class="label" style="margin-top:12px">文明特色</p><div class="civs">' + E.CIVS.map(function (c) { return '<span>' + c.icon + ' ' + c.name + '：' + esc(c.bonus) + '</span>'; }).join('') + '</div></div>' +
      '<div class="m-actions"><button type="button" class="btn primary big" id="mOk">' + (first ? '开始吧' : '知道了') + '</button></div>');
    $('#mOk').addEventListener('click', function () { closeModal(); if (first && game) queueModals(); });
  }
  function showMenu() {
    showModal('<h2>菜单</h2><div class="m-actions">' +
      '<button type="button" class="btn" id="mHelp">玩法说明</button>' +
      '<button type="button" class="btn" id="mHome">保存并回到首页</button>' +
      '<button type="button" class="btn" id="mRestart" style="color:var(--seal)">放弃本局，重新开始</button>' +
      '<button type="button" class="btn ghost" id="mClose">继续游戏</button></div>');
    $('#mHelp').addEventListener('click', function () { showHelp(false); });
    $('#mHome').addEventListener('click', function () { closeModal(); save(); showScreen('start'); });
    $('#mRestart').addEventListener('click', function () { closeModal(); store.del(SAVE_KEY); startGame(); });
    $('#mClose').addEventListener('click', closeModal);
  }
  function copyText(text, btn) {
    var done = function () { if (btn) btn.textContent = '已复制'; };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else { fallbackCopy(text, done); }
  }
  function fallbackCopy(text, done) {
    var ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { toast('复制失败，请长按选择文字'); }
    document.body.removeChild(ta);
  }
  function toast(text, ok) {
    var t = $('#toast');
    t.textContent = text; t.className = 'toast' + (ok ? ' ok' : ''); t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.hidden = true; }, ok ? 1400 : 2400);
  }

  // ------------------------------------------------------------ 事件绑定与启动
  function bindGame() {
    $('#board').addEventListener('click', function (e) {
      var b = e.target.closest('.tile'); if (!b) return;
      onTile(Number(b.getAttribute('data-idx')));
    });
    $('#cards').addEventListener('click', function (e) {
      var b = e.target.closest('.card'); if (!b) return;
      onCard(b.getAttribute('data-type'), b.getAttribute('data-id'));
    });
    $('#tabs').addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      setTab(b.getAttribute('data-tab'));
    });
    $('#btnEnd').addEventListener('click', endTurn);
    $('#btnMenu').addEventListener('click', showMenu);
    $('#modal').addEventListener('click', function (e) {
      // 事件卡、交接、结算这些需要明确确认的弹层不点背景关闭；菜单与帮助可以
      if (e.target !== e.currentTarget) return;
      if ($('#mClose') || ($('#mOk') && $('#modalCard').querySelector('.help'))) closeModal();
    });
  }

  function boot(data) {
    initStart(); bindGame();
    if (data && data.save) {
      try { game = E.load(data.save); seenTurn = data.seenTurn || 0; tab = data.tab || 'build'; setTab(tab); showScreen('game'); afterChange(); return; } catch (e) { /* 回退到首页 */ }
    }
    showScreen('start');
  }
  var hot = window.claude && window.claude.hot;
  if (hot && hot.snapshot) hot.snapshot(function () { return { save: game && !$('#game').hidden ? E.serialize(game) : null, seenTurn: seenTurn, tab: tab }; });
  if (hot && hot.ready) hot.ready(boot); else boot((hot && hot.data) || {});
})();
