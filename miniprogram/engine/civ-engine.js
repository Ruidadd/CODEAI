/*
 * 文明小桌 · 核心规则引擎
 * ------------------------------------------------------------
 * 零依赖、无 UI，可在微信小程序 / 浏览器 / Node 中直接运行。
 * 游戏状态是一个纯 JSON 对象，随时可以 JSON.stringify 存档。
 *
 * 玩法速览：
 *   - 8×8 棋盘，每回合先收入资源，再做任意次可负担的操作，然后结束回合
 *   - 🌾粮食 → 扩张领土（点格子）  ⚒️生产 → 建筑 / 奇观  🔬科技 → 研究
 *   - 🎭文化就是分数；每 3 回合翻一张事件卡；20 回合后分高者胜
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) { module.exports = factory(); }
  else { root.CivEngine = factory(); }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // ------------------------------------------------------------
  // 常量与数据表
  // ------------------------------------------------------------
  var W = 8, H = 8, MAX_ROUND = 20, EVENT_EVERY = 3;
  var ACTIONS_PER_TURN = 3;          // 每回合最多行动次数（扩张/建造/研究/奇观各算 1 次）
  var EXPAND_QUAD = 10;              // 扩张费 = 2 + 领土数 + 领土数²/EXPAND_QUAD
  var START_POS = [[1, 1], [6, 6], [6, 1], [1, 6]];
  var START_RES = { F: 3, P: 4, S: 0 };
  var CAPITAL_YIELD = { F: 2, P: 1, S: 1 };
  var SCORE = { tile: 1, building: 2, tech: 2, wonder: 5, era: 2 };
  // 可重复的资源出口：粮食多了办庆典，科技点满后研究未来科技
  var FESTIVAL = { id: 'festival', name: '庆典', icon: '🎊', cost: 5, gain: 1, effect: '消耗粮食换取文化，可重复' };
  var FUTURE = { id: 'future', name: '未来科技', icon: '🚀', cost: 12, gain: 2, effect: '所有科技研究完后可重复研究' };
  var DIFFICULTY = { easy: 0.8, normal: 1, hard: 1.3 };

  var RES = {
    F: { name: '粮食', icon: '🌾', use: '扩张领土' },
    P: { name: '生产', icon: '⚒️', use: '建筑与奇观' },
    S: { name: '科技', icon: '🔬', use: '研究' },
    C: { name: '文化', icon: '🎭', use: '分数' }
  };
  var RES_KEYS = ['F', 'P', 'S', 'C'];

  var TERRAINS = {
    grass:     { name: '平原',   icon: '🌾', yields: { F: 1 } },
    forest:    { name: '森林',   icon: '🌲', yields: { P: 1 } },
    mountain:  { name: '山地',   icon: '⛰️', yields: { P: 1 } },
    river:     { name: '河谷',   icon: '🏞️', yields: { S: 1 } },
    desert:    { name: '沙漠',   icon: '🏜️', yields: { P: 1 }, costMod: -1 },
    ocean:     { name: '海洋',   icon: '🌊', yields: { F: 1, S: 1 }, needTech: 'sailing' },
    ruins:     { name: '遗迹',   icon: '🏺', yields: { S: 1 }, bonus: true },
    natwonder: { name: '自然奇观', icon: '🗻', yields: { F: 1, S: 1, C: 1 } }
  };
  var TERRAIN_WEIGHTS = [['grass', 30], ['forest', 24], ['mountain', 14], ['river', 16], ['desert', 8]];

  var CIVS = [
    { id: 'china',  name: '华夏', icon: '🐉', color: '#c0392b', passive: 'sci',      bonus: '每回合 +1🔬，科技造价 -1' },
    { id: 'rome',   name: '罗马', icon: '🦅', color: '#7d3c98', passive: 'expand',   bonus: '扩张所需🌾 -2' },
    { id: 'egypt',  name: '埃及', icon: '🐫', color: '#d68910', passive: 'wonder',   bonus: '奇观造价 -4' },
    { id: 'greece', name: '希腊', icon: '🏛️', color: '#2874a6', passive: 'culture',  bonus: '每回合 +1🎭，庆典只需 3🌾' },
    { id: 'persia', name: '波斯', icon: '🦁', color: '#148f77', passive: 'prod',     bonus: '每回合额外 +1⚒️' },
    { id: 'inca',   name: '印加', icon: '🦙', color: '#b9770e', passive: 'mountain', bonus: '每块山地额外 +2🌾' }
  ];

  var ERAS = ['远古时代', '古典时代', '中世纪', '文艺复兴', '工业时代'];
  var TECHS = [
    { id: 'agri',       era: 0, name: '农业',   icon: '🌱', cost: 5,  effect: '每块平原 +1🌾' },
    { id: 'mining',     era: 0, name: '采矿',   icon: '⛏️', cost: 5,  effect: '每块山地 +1⚒️' },
    { id: 'writing',    era: 0, name: '文字',   icon: '📜', cost: 6,  effect: '解锁 图书馆、亚历山大图书馆' },
    { id: 'currency',   era: 1, name: '货币',   icon: '🪙', cost: 7,  effect: '解锁 市场' },
    { id: 'masonry',    era: 1, name: '建筑学', icon: '🧱', cost: 7,  effect: '解锁 城墙、长城' },
    { id: 'philosophy', era: 1, name: '哲学',   icon: '🤔', cost: 8,  effect: '解锁 神庙' },
    { id: 'sailing',    era: 2, name: '航海术', icon: '⛵', cost: 10, effect: '每块河谷 +1🔬，可扩张到海洋，解锁 港口、灯塔' },
    { id: 'feudalism',  era: 2, name: '封建制', icon: '🏰', cost: 10,  effect: '每块森林 +1⚒️，解锁 庄园、紫禁城' },
    { id: 'theology',   era: 2, name: '神学',   icon: '📿', cost: 11,  effect: '解锁 修道院、大教堂' },
    { id: 'printing',   era: 3, name: '印刷术', icon: '📚', cost: 13,  effect: '解锁 大学' },
    { id: 'gunpowder',  era: 3, name: '火药',   icon: '💥', cost: 13,  effect: '解锁 兵工厂' },
    { id: 'banking',    era: 3, name: '银行业', icon: '🏦', cost: 14, effect: '解锁 银行' }
  ];
  var TECHS_PER_ERA = 3;

  var BUILDINGS = [
    { id: 'granary',    name: '粮仓',   icon: '🏚️', cost: 5,  yields: { F: 2 } },
    { id: 'workshop',   name: '作坊',   icon: '🔨', cost: 6,  yields: { P: 2 } },
    { id: 'shrine',     name: '祭坛',   icon: '🕯️', cost: 5,  yields: { C: 1 } },
    { id: 'library',    name: '图书馆', icon: '📖', cost: 8,  yields: { S: 2 }, tech: 'writing' },
    { id: 'market',     name: '市场',   icon: '🏪', cost: 9,  yields: { F: 1, P: 1, S: 1 }, tech: 'currency' },
    { id: 'walls',      name: '城墙',   icon: '🧱', cost: 6,  yields: {}, tech: 'masonry', protect: true },
    { id: 'temple',     name: '神庙',   icon: '⛩️', cost: 9,  yields: { C: 2 }, tech: 'philosophy' },
    { id: 'harbor',     name: '港口',   icon: '⚓', cost: 9,  yields: { F: 1, S: 1 }, tech: 'sailing' },
    { id: 'manor',      name: '庄园',   icon: '🏡', cost: 10, yields: { F: 2 }, tech: 'feudalism' },
    { id: 'monastery',  name: '修道院', icon: '🛕', cost: 10, yields: { S: 1, C: 1 }, tech: 'theology' },
    { id: 'university', name: '大学',   icon: '🎓', cost: 12, yields: { S: 2 }, tech: 'printing' },
    { id: 'armory',     name: '兵工厂', icon: '⚔️', cost: 12, yields: { P: 2 }, tech: 'gunpowder' },
    { id: 'bank',       name: '银行',   icon: '💰', cost: 13, yields: { F: 2, P: 1 }, tech: 'banking' }
  ];

  var WONDERS = [
    { id: 'stonehenge', name: '巨石阵',       icon: '🪨', cost: 14, yields: { C: 2 } },
    { id: 'gardens',    name: '空中花园',     icon: '🌺', cost: 18, yields: { F: 3 }, tech: 'agri' },
    { id: 'pyramids',   name: '金字塔',       icon: '🔺', cost: 18, yields: { P: 3 }, tech: 'mining' },
    { id: 'alexandria', name: '亚历山大图书馆', icon: '🏛️', cost: 18, yields: { S: 3 }, tech: 'writing' },
    { id: 'greatwall',  name: '长城',         icon: '🏯', cost: 22, yields: { C: 2 }, tech: 'masonry', protect: true },
    { id: 'lighthouse', name: '灯塔',         icon: '🗼', cost: 22, yields: { F: 2, S: 2 }, tech: 'sailing' },
    { id: 'forbidden',  name: '紫禁城',       icon: '🏮', cost: 26, yields: { F: 2, P: 2, S: 2 }, tech: 'feudalism' },
    { id: 'notredame',  name: '大教堂',       icon: '⛪', cost: 26, yields: { C: 3 }, tech: 'theology' }
  ];

  var EVENTS = [
    { id: 'harvest',    name: '丰收',     icon: '🌾', text: '风调雨顺，所有文明 +4🌾' },
    { id: 'discovery',  name: '灵感迸发', icon: '💡', text: '学者辈出，所有文明 +3🔬' },
    { id: 'boom',       name: '百业兴旺', icon: '🏗️', text: '工匠云集，所有文明 +3⚒️' },
    { id: 'barbarians', name: '蛮族来袭', icon: '🪓', text: '没有城墙或长城的文明 -3🌾 -3⚒️' },
    { id: 'plague',     name: '瘟疫',     icon: '🦠', text: '疾病蔓延，所有文明 -3🌾' },
    { id: 'festival',   name: '文化节',   icon: '🎉', text: '载歌载舞，所有文明 +2🎭' },
    { id: 'quake',      name: '地震',     icon: '🌋', text: '房屋受损，所有文明 -2⚒️' },
    { id: 'golden',     name: '盛世',     icon: '☀️', text: '国泰民安，所有文明 +2🌾 +2⚒️ +2🔬' }
  ];

  // ------------------------------------------------------------
  // 小工具
  // ------------------------------------------------------------
  function byId(list, id) {
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }
  function has(arr, id) { return arr.indexOf(id) >= 0; }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function yieldText(y) {
    var parts = [];
    for (var i = 0; i < RES_KEYS.length; i++) {
      var k = RES_KEYS[i];
      if (y[k]) parts.push('+' + y[k] + RES[k].icon);
    }
    return parts.join(' ');
  }
  function addYields(target, y, mult) {
    mult = mult || 1;
    for (var i = 0; i < RES_KEYS.length; i++) {
      var k = RES_KEYS[i];
      if (y[k]) target[k] += y[k] * mult;
    }
  }

  // 可序列化的随机数（mulberry32），状态存在 game.rng 里
  function rand(game) {
    var t = (game.rng = (game.rng + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  function randInt(game, n) { return Math.floor(rand(game) * n); }
  function shuffle(game, arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = randInt(game, i + 1), t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function weightedPick(game, pairs) {
    var total = 0, i;
    for (i = 0; i < pairs.length; i++) total += pairs[i][1];
    var r = rand(game) * total;
    for (i = 0; i < pairs.length; i++) {
      r -= pairs[i][1];
      if (r < 0) return pairs[i][0];
    }
    return pairs[pairs.length - 1][0];
  }

  function idxOf(x, y) { return y * W + x; }
  function neighbors(idx) {
    var x = idx % W, y = Math.floor(idx / W), out = [];
    if (x > 0) out.push(idx - 1);
    if (x < W - 1) out.push(idx + 1);
    if (y > 0) out.push(idx - W);
    if (y < H - 1) out.push(idx + W);
    return out;
  }

  function log(game, pi, text) {
    game.log.push({ r: game.round, p: pi, t: text });
    if (game.log.length > 60) game.log.splice(0, game.log.length - 60);
  }

  // ------------------------------------------------------------
  // 地图生成
  // ------------------------------------------------------------
  function genTiles(game) {
    var tiles = [], i;
    for (i = 0; i < W * H; i++) tiles.push({ t: weightedPick(game, TERRAIN_WEIGHTS), o: -1, cap: false });

    // 出生点及其四邻保留为陆地，保证每个文明开局都有地可扩
    var reserved = {};
    for (i = 0; i < game.players.length; i++) {
      var s = idxOf(START_POS[i][0], START_POS[i][1]);
      reserved[s] = true;
      var nb = neighbors(s);
      for (var k = 0; k < nb.length; k++) reserved[nb[k]] = true;
    }
    function freeTile() {
      for (var tries = 0; tries < 200; tries++) {
        var idx = randInt(game, W * H);
        if (!reserved[idx] && tiles[idx].t !== 'ocean') return idx;
      }
      return -1;
    }

    // 1~2 片海洋
    var blobs = 1 + (rand(game) < 0.5 ? 1 : 0);
    for (var b = 0; b < blobs; b++) {
      var seed = freeTile();
      if (seed < 0) break;
      var target = 3 + randInt(game, 3), count = 0, queue = [seed];
      while (queue.length && count < target) {
        var cur = queue.shift();
        if (reserved[cur] || tiles[cur].t === 'ocean') continue;
        tiles[cur].t = 'ocean'; count++;
        var ns = shuffle(game, neighbors(cur));
        for (var q = 0; q < ns.length; q++) queue.push(ns[q]);
      }
    }
    // 3 处遗迹、1 处自然奇观
    for (i = 0; i < 3; i++) { var r = freeTile(); if (r >= 0) { tiles[r].t = 'ruins'; reserved[r] = true; } }
    var nw = freeTile();
    if (nw >= 0) { tiles[nw].t = 'natwonder'; reserved[nw] = true; }

    // 首都
    for (i = 0; i < game.players.length; i++) {
      var c = idxOf(START_POS[i][0], START_POS[i][1]);
      tiles[c].t = 'grass'; tiles[c].o = i; tiles[c].cap = true;
    }
    game.tiles = tiles;
  }

  // ------------------------------------------------------------
  // 对局创建 / 回合推进
  // ------------------------------------------------------------
  function dailySeed(date) {
    var d = date || new Date();
    return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
  }

  function createGame(opts) {
    opts = opts || {};
    var seed = (opts.seed === undefined || opts.seed === null) ? (Date.now() % 2147483647) : opts.seed;
    seed = (Number(seed) >>> 0) || 1;
    var game = {
      v: 1, seed: seed, rng: seed, mode: opts.mode || 'random',
      difficulty: DIFFICULTY[opts.difficulty] ? opts.difficulty : 'normal',
      w: W, h: H, round: 1, maxRound: opts.maxRound || MAX_ROUND, cur: 0, phase: 'playing', turnNo: 0,
      tiles: [], players: [], wondersBuilt: {}, eventDeck: [], pendingEvent: null, lastEventRound: 0,
      log: [], winner: -1
    };

    var specs = (opts.players && opts.players.length) ? opts.players.slice(0, 4)
      : [{ civ: 'china', isHuman: true }, { civ: 'rome', isHuman: false }];
    var used = {};
    specs.forEach(function (s) { if (s.civ && byId(CIVS, s.civ) && !used[s.civ]) { used[s.civ] = true; } else { s.civ = null; } });
    specs.forEach(function (s) {
      if (!s.civ) {
        var pool = CIVS.filter(function (c) { return !used[c.id]; });
        var pick = pool[randInt(game, pool.length)];
        s.civ = pick.id; used[pick.id] = true;
      }
    });
    game.players = specs.map(function (s) {
      var civ = byId(CIVS, s.civ);
      return {
        civ: civ.id, name: s.name || civ.name, isHuman: !!s.isHuman,
        res: clone(START_RES), culture: 0, techs: [], buildings: [], wonders: [],
        income: { F: 0, P: 0, S: 0, C: 0 }
      };
    });
    genTiles(game);
    game.eventDeck = shuffle(game, EVENTS.map(function (e) { return e.id; }));
    log(game, -1, '新的文明在这片土地上诞生了');
    startTurn(game);
    runAI(game);
    return game;
  }

  function startTurn(game) {
    game.turnNo++;
    var p = game.players[game.cur];
    if (game.cur === 0 && game.round % EVENT_EVERY === 0 && game.lastEventRound !== game.round) drawEvent(game);
    var inc = computeIncome(game, game.cur);
    p.res.F += inc.F; p.res.P += inc.P; p.res.S += inc.S; p.culture += inc.C;
    p.income = inc;
    p.actions = 0;
  }
  function actionsLeft(game) { return ACTIONS_PER_TURN - (game.players[game.cur].actions || 0); }

  function advance(game) {
    var n = game.players.length;
    game.cur = (game.cur + 1) % n;
    if (game.cur === 0) game.round++;
    if (game.round > game.maxRound) { finish(game); return; }
    startTurn(game);
  }

  function runAI(game) {
    var guard = 0;
    while (game.phase === 'playing' && !game.players[game.cur].isHuman && guard++ < 500) {
      aiTurn(game);
      advance(game);
    }
  }

  function endTurn(game) {
    if (game.phase !== 'playing') return game;
    advance(game);
    runAI(game);
    return game;
  }

  function finish(game) {
    game.phase = 'over';
    game.round = game.maxRound;
    var best = -1, bestScore = -1;
    for (var i = 0; i < game.players.length; i++) {
      var s = computeScore(game, i);
      if (s > bestScore) { bestScore = s; best = i; }
    }
    game.winner = best;
    log(game, -1, '时代落幕，' + game.players[best].name + ' 以 ' + bestScore + ' 分成为最伟大的文明');
  }

  // ------------------------------------------------------------
  // 事件
  // ------------------------------------------------------------
  function isProtected(p) { return has(p.buildings, 'walls') || has(p.wonders, 'greatwall'); }

  function applyEvent(id, p) {
    var r = p.res;
    switch (id) {
      case 'harvest': r.F += 4; break;
      case 'discovery': r.S += 3; break;
      case 'boom': r.P += 3; break;
      case 'barbarians': if (!isProtected(p)) { r.F = Math.max(0, r.F - 3); r.P = Math.max(0, r.P - 3); } break;
      case 'plague': r.F = Math.max(0, r.F - 3); break;
      case 'festival': p.culture += 2; break;
      case 'quake': r.P = Math.max(0, r.P - 2); break;
      case 'golden': r.F += 2; r.P += 2; r.S += 2; break;
    }
  }

  function drawEvent(game) {
    if (!game.eventDeck.length) game.eventDeck = shuffle(game, EVENTS.map(function (e) { return e.id; }));
    var id = game.eventDeck.shift(), ev = byId(EVENTS, id);
    for (var i = 0; i < game.players.length; i++) applyEvent(id, game.players[i]);
    game.pendingEvent = { id: id, round: game.round };
    game.lastEventRound = game.round;
    log(game, -1, '事件「' + ev.name + '」' + ev.text);
  }

  function ackEvent(game) { game.pendingEvent = null; return game; }

  // ------------------------------------------------------------
  // 收入 / 花费 / 分数
  // ------------------------------------------------------------
  function eraOf(p) { return Math.min(ERAS.length - 1, Math.floor(p.techs.length / TECHS_PER_ERA)); }
  function countTiles(game, pi) {
    var n = 0;
    for (var i = 0; i < game.tiles.length; i++) if (game.tiles[i].o === pi) n++;
    return n;
  }

  function tileYield(game, pi, tile) {
    var p = game.players[pi], civ = byId(CIVS, p.civ), y = { F: 0, P: 0, S: 0, C: 0 };
    if (tile.cap) { addYields(y, CAPITAL_YIELD); return y; }
    addYields(y, TERRAINS[tile.t].yields);
    if (tile.t === 'grass' && has(p.techs, 'agri')) y.F += 1;
    if (tile.t === 'forest' && has(p.techs, 'feudalism')) y.P += 1;
    if (tile.t === 'river' && has(p.techs, 'sailing')) y.S += 1;
    if (tile.t === 'mountain') {
      if (has(p.techs, 'mining')) y.P += 1;
      if (civ.passive === 'mountain') y.F += 2;
    }
    return y;
  }

  function computeIncome(game, pi) {
    var p = game.players[pi], civ = byId(CIVS, p.civ), inc = { F: 0, P: 0, S: 0, C: 0 }, i;
    for (i = 0; i < game.tiles.length; i++) if (game.tiles[i].o === pi) addYields(inc, tileYield(game, pi, game.tiles[i]));
    for (i = 0; i < p.buildings.length; i++) addYields(inc, byId(BUILDINGS, p.buildings[i]).yields);
    for (i = 0; i < p.wonders.length; i++) addYields(inc, byId(WONDERS, p.wonders[i]).yields);
    if (civ.passive === 'sci') inc.S += 1;
    if (civ.passive === 'prod') inc.P += 1;
    if (civ.passive === 'culture') inc.C += 1;
    if (!p.isHuman) {
      var f = DIFFICULTY[game.difficulty] || 1;
      inc.F = Math.round(inc.F * f); inc.P = Math.round(inc.P * f); inc.S = Math.round(inc.S * f);
    }
    return inc;
  }

  function expandCost(game, pi, idx) {
    var p = game.players[pi], civ = byId(CIVS, p.civ);
    var n = countTiles(game, pi);
    var cost = 2 + n + Math.floor(n * n / EXPAND_QUAD);
    cost += TERRAINS[game.tiles[idx].t].costMod || 0;
    if (civ.passive === 'expand') cost -= 2;
    return Math.max(1, cost);
  }

  function buildCost(game, pi, b) { return b.cost + game.players[pi].buildings.length; }
  function techCost(game, pi, t) {
    var p = game.players[pi];
    return Math.max(1, t.cost + p.techs.length - (byId(CIVS, p.civ).passive === 'sci' ? 1 : 0));
  }
  function festivalCost(game, pi) { return FESTIVAL.cost - (byId(CIVS, game.players[pi].civ).passive === 'culture' ? 2 : 0); }

  function wonderCost(game, pi, w) {
    var civ = byId(CIVS, game.players[pi].civ);
    return Math.max(1, w.cost - (civ.passive === 'wonder' ? 4 : 0));
  }

  function isClaimable(game, pi, idx) {
    var tile = game.tiles[idx];
    if (tile.o !== -1) return false;
    var need = TERRAINS[tile.t].needTech;
    if (need && !has(game.players[pi].techs, need)) return false;
    var nb = neighbors(idx);
    for (var i = 0; i < nb.length; i++) if (game.tiles[nb[i]].o === pi) return true;
    return false;
  }

  function computeScore(game, pi) {
    var p = game.players[pi];
    return countTiles(game, pi) * SCORE.tile + p.buildings.length * SCORE.building +
      p.techs.length * SCORE.tech + p.wonders.length * SCORE.wonder + p.culture;
  }

  // ------------------------------------------------------------
  // 合法操作与执行
  // ------------------------------------------------------------
  function getLegalActions(game) {
    var acts = [];
    if (game.phase !== 'playing' || actionsLeft(game) <= 0) return acts;
    var pi = game.cur, p = game.players[pi], i, era = eraOf(p);
    for (i = 0; i < game.tiles.length; i++) {
      if (!isClaimable(game, pi, i)) continue;
      var c = expandCost(game, pi, i);
      if (p.res.F >= c) acts.push({ type: 'expand', idx: i, cost: c });
    }
    for (i = 0; i < BUILDINGS.length; i++) {
      var b = BUILDINGS[i];
      if (has(p.buildings, b.id)) continue;
      if (b.tech && !has(p.techs, b.tech)) continue;
      var bc = buildCost(game, pi, b);
      if (p.res.P >= bc) acts.push({ type: 'build', id: b.id, cost: bc });
    }
    for (i = 0; i < WONDERS.length; i++) {
      var w = WONDERS[i];
      if (game.wondersBuilt[w.id] !== undefined) continue;
      if (w.tech && !has(p.techs, w.tech)) continue;
      var wc = wonderCost(game, pi, w);
      if (p.res.P >= wc) acts.push({ type: 'wonder', id: w.id, cost: wc });
    }
    for (i = 0; i < TECHS.length; i++) {
      var t = TECHS[i];
      if (has(p.techs, t.id) || t.era !== era) continue;
      var tc = techCost(game, pi, t);
      if (p.res.S >= tc) acts.push({ type: 'research', id: t.id, cost: tc });
    }
    var fc = festivalCost(game, pi);
    if (p.res.F >= fc) acts.push({ type: 'festival', id: FESTIVAL.id, cost: fc });
    if (p.techs.length >= TECHS.length && p.res.S >= FUTURE.cost) acts.push({ type: 'future', id: FUTURE.id, cost: FUTURE.cost });
    return acts;
  }

  function lootRuins(game, pi) {
    var p = game.players[pi], roll = randInt(game, 4), text;
    if (roll === 0) { p.res.F += 5; text = '+5🌾'; }
    else if (roll === 1) { p.res.P += 5; text = '+5⚒️'; }
    else if (roll === 2) { p.res.S += 5; text = '+5🔬'; }
    else { p.culture += 3; text = '+3🎭'; }
    return text;
  }

  function applyAction(game, action) {
    if (game.phase !== 'playing') return { ok: false, msg: '对局已结束' };
    if (!action) return { ok: false, msg: '无效操作' };
    if (action.type === 'end') { endTurn(game); return { ok: true }; }
    var pi = game.cur, p = game.players[pi], legal = getLegalActions(game), found = null;
    for (var i = 0; i < legal.length; i++) {
      var a = legal[i];
      if (a.type !== action.type) continue;
      if (a.type === 'expand' ? a.idx === action.idx : a.id === action.id) { found = a; break; }
    }
    if (!found) return { ok: false, msg: explainIllegal(game, action) };

    p.actions = (p.actions || 0) + 1;
    var msg = '';
    if (found.type === 'expand') {
      var tile = game.tiles[found.idx];
      p.res.F -= found.cost; tile.o = pi;
      msg = '占领了' + TERRAINS[tile.t].name;
      if (tile.t === 'ruins' && !tile.looted) { tile.looted = true; msg += '，在遗迹中发现 ' + lootRuins(game, pi); }
      if (tile.t === 'natwonder') msg += '，壮丽的景色让人心旷神怡';
    } else if (found.type === 'build') {
      p.res.P -= found.cost; p.buildings.push(found.id);
      msg = '建造了' + byId(BUILDINGS, found.id).name;
    } else if (found.type === 'wonder') {
      p.res.P -= found.cost; p.wonders.push(found.id); game.wondersBuilt[found.id] = pi;
      msg = '建成奇观「' + byId(WONDERS, found.id).name + '」！';
    } else if (found.type === 'research') {
      var before = eraOf(p);
      p.res.S -= found.cost; p.techs.push(found.id);
      msg = '研究了' + byId(TECHS, found.id).name;
      var after = eraOf(p);
      if (after > before) { p.culture += SCORE.era; msg += '，迈入' + ERAS[after] + '（+' + SCORE.era + '🎭）'; }
    } else if (found.type === 'festival') {
      p.res.F -= found.cost; p.culture += FESTIVAL.gain; p.festivals = (p.festivals || 0) + 1;
      msg = '举办了庆典（+' + FESTIVAL.gain + '🎭）';
    } else if (found.type === 'future') {
      p.res.S -= found.cost; p.culture += FUTURE.gain; p.futureTechs = (p.futureTechs || 0) + 1;
      msg = '研究了未来科技（+' + FUTURE.gain + '🎭）';
    }
    log(game, pi, msg);
    return { ok: true, msg: msg };
  }

  function explainIllegal(game, action) {
    var pi = game.cur, p = game.players[pi];
    if (actionsLeft(game) <= 0) return '本回合的 ' + ACTIONS_PER_TURN + ' 次行动已用完，请结束回合';
    if (action.type === 'expand') {
      var tile = game.tiles[action.idx];
      if (!tile) return '无效格子';
      if (tile.o === pi) return '这已经是你的领土';
      if (tile.o !== -1) return '这是 ' + game.players[tile.o].name + ' 的领土';
      if (TERRAINS[tile.t].needTech && !has(p.techs, TERRAINS[tile.t].needTech)) return '需要先研究「航海术」才能占领海洋';
      if (!isClaimable(game, pi, action.idx)) return '只能占领与自己领土相邻的格子';
      return '粮食不足，需要 ' + expandCost(game, pi, action.idx) + '🌾';
    }
    if (action.type === 'build') {
      var b = byId(BUILDINGS, action.id);
      if (!b) return '无效建筑';
      if (has(p.buildings, b.id)) return '已经建造过了';
      if (b.tech && !has(p.techs, b.tech)) return '需要先研究「' + byId(TECHS, b.tech).name + '」';
      return '生产不足，需要 ' + buildCost(game, pi, b) + '⚒️';
    }
    if (action.type === 'wonder') {
      var w = byId(WONDERS, action.id);
      if (!w) return '无效奇观';
      if (game.wondersBuilt[w.id] !== undefined) return '已被 ' + game.players[game.wondersBuilt[w.id]].name + ' 抢先建成';
      if (w.tech && !has(p.techs, w.tech)) return '需要先研究「' + byId(TECHS, w.tech).name + '」';
      return '生产不足，需要 ' + wonderCost(game, pi, w) + '⚒️';
    }
    if (action.type === 'research') {
      var t = byId(TECHS, action.id);
      if (!t) return '无效科技';
      if (has(p.techs, t.id)) return '已经研究过了';
      if (t.era !== eraOf(p)) return t.era > eraOf(p) ? '先研究完本时代的科技' : '已经研究过了';
      return '科技不足，需要 ' + techCost(game, pi, t) + '🔬';
    }
    if (action.type === 'festival') return '粮食不足，需要 ' + festivalCost(game, pi) + '🌾';
    if (action.type === 'future') return p.techs.length < TECHS.length ? '先研究完全部科技' : '科技不足，需要 ' + FUTURE.cost + '🔬';
    return '无效操作';
  }

  // ------------------------------------------------------------
  // 电脑玩家（简单贪心，带一点随机）
  // ------------------------------------------------------------
  var AI_WEIGHT = { F: 1, P: 1.2, S: 1.3, C: 1.4 };

  function tileValue(game, pi, idx) {
    var tile = game.tiles[idx], y = tileYield(game, pi, tile), v = 0, k;
    for (k in AI_WEIGHT) v += (y[k] || 0) * AI_WEIGHT[k];
    if (tile.t === 'ruins' && !tile.looted) v += 3;
    if (tile.t === 'natwonder') v += 4;
    var nb = neighbors(idx);
    for (var i = 0; i < nb.length; i++) if (game.tiles[nb[i]].o === -1 && game.tiles[nb[i]].t !== 'ocean') v += 0.3;
    return v;
  }

  function buildValue(game, pi, id) {
    var b = byId(BUILDINGS, id), v = 0, k;
    for (k in AI_WEIGHT) v += (b.yields[k] || 0) * AI_WEIGHT[k];
    if (b.protect) v += 1;
    return v / buildCost(game, pi, b) * 10;
  }

  function pickBest(list, keyFn) {
    var best = null, bestV = -Infinity;
    for (var i = 0; i < list.length; i++) {
      var v = keyFn(list[i]);
      if (v > bestV) { bestV = v; best = list[i]; }
    }
    return best;
  }

  function chooseAiAction(game, acts) {
    var pi = game.cur, p = game.players[pi], groups = { expand: [], build: [], wonder: [], research: [], festival: [], future: [] }, i;
    for (i = 0; i < acts.length; i++) groups[acts[i].type].push(acts[i]);
    if (groups.wonder.length) return pickBest(groups.wonder, function (a) { return a.cost; });
    if (groups.future.length) return groups.future[0];
    var order = game.round <= 8 ? ['expand', 'build', 'research'] : ['research', 'build', 'expand'];
    if (rand(game) < 0.25) { var t = order[0]; order[0] = order[1]; order[1] = t; }
    for (i = 0; i < order.length; i++) {
      var g = groups[order[i]];
      if (!g.length) continue;
      if (order[i] === 'expand') return pickBest(g, function (a) { return tileValue(game, pi, a.idx) + rand(game) * 0.5; });
      if (order[i] === 'build') return pickBest(g, function (a) { return buildValue(game, pi, a.id); });
      return pickBest(g, function (a) { return -a.cost; });
    }
    // 扩张不动、粮食又堆得太多时，办庆典换文化
    if (groups.festival.length && !groups.expand.length && p.res.F >= 12) return groups.festival[0];
    return null;
  }

  function aiTurn(game) {
    for (var guard = 0; guard < 12; guard++) {
      var acts = getLegalActions(game);
      if (!acts.length) break;
      var a = chooseAiAction(game, acts);
      if (!a) break;
      applyAction(game, a);
    }
  }

  // ------------------------------------------------------------
  // 视图模型：UI 只需照着渲染，不用懂规则
  // ------------------------------------------------------------
  function playerView(game, i) {
    var p = game.players[i], civ = byId(CIVS, p.civ);
    return {
      idx: i, name: p.name, civName: civ.name, icon: civ.icon, color: civ.color, isHuman: p.isHuman,
      score: computeScore(game, i), tiles: countTiles(game, i), era: eraOf(p), eraName: ERAS[eraOf(p)],
      techs: p.techs.length, buildings: p.buildings.length,
      wonders: p.wonders.map(function (id) { var w = byId(WONDERS, id); return w.icon + w.name; }),
      isCur: i === game.cur
    };
  }

  function getView(game) {
    var pi = game.cur, p = game.players[pi], civ = byId(CIVS, p.civ);
    var humanTurn = game.phase === 'playing' && p.isHuman;
    var legal = humanTurn ? getLegalActions(game) : [];
    var legalExpand = {}, legalIds = {}, i;
    for (i = 0; i < legal.length; i++) {
      if (legal[i].type === 'expand') legalExpand[legal[i].idx] = legal[i].cost;
      else legalIds[legal[i].type + ':' + legal[i].id] = true;
    }

    var tiles = [];
    for (i = 0; i < game.tiles.length; i++) {
      var t = game.tiles[i], terr = TERRAINS[t.t], owner = t.o >= 0 ? byId(CIVS, game.players[t.o].civ) : null;
      var claimable = humanTurn && isClaimable(game, pi, i);
      tiles.push({
        idx: i, x: i % W, y: Math.floor(i / W), terrain: t.t, name: t.cap ? '首都' : terr.name,
        icon: t.cap ? owner.icon : terr.icon, owner: t.o, color: owner ? owner.color : '',
        isCap: t.cap, looted: !!t.looted,
        claimable: claimable, affordable: legalExpand[i] !== undefined,
        cost: claimable ? expandCost(game, pi, i) : 0,
        yieldText: yieldText(t.o >= 0 ? tileYield(game, t.o, t) : (t.cap ? CAPITAL_YIELD : terr.yields))
      });
    }

    var buildings = BUILDINGS.map(function (b) {
      var state, lockText = '';
      if (has(p.buildings, b.id)) state = 'done';
      else if (b.tech && !has(p.techs, b.tech)) { state = 'locked'; lockText = '需要 ' + byId(TECHS, b.tech).name; }
      else state = legalIds['build:' + b.id] ? 'ok' : 'poor';
      var cost = buildCost(game, pi, b);
      return { id: b.id, name: b.name, icon: b.icon, cost: cost, costText: cost + '⚒️', state: state, lockText: lockText,
        effect: (yieldText(b.yields) || '') + (b.protect ? (yieldText(b.yields) ? ' · ' : '') + '免疫蛮族' : '') };
    });
    var fcost = festivalCost(game, pi);
    buildings.push({ id: FESTIVAL.id, name: FESTIVAL.name, icon: FESTIVAL.icon, cost: fcost, costText: fcost + '🌾',
      state: legalIds['festival:' + FESTIVAL.id] ? 'ok' : 'poor', lockText: '', repeat: true, effect: '+' + FESTIVAL.gain + '🎭 · ' + FESTIVAL.effect });
    var wonders = WONDERS.map(function (w) {
      var state, lockText = '', builtBy = game.wondersBuilt[w.id], cost = wonderCost(game, pi, w);
      if (builtBy !== undefined) { state = builtBy === pi ? 'done' : 'taken'; lockText = game.players[builtBy].name + ' 已建成'; }
      else if (w.tech && !has(p.techs, w.tech)) { state = 'locked'; lockText = '需要 ' + byId(TECHS, w.tech).name; }
      else state = legalIds['wonder:' + w.id] ? 'ok' : 'poor';
      return { id: w.id, name: w.name, icon: w.icon, cost: cost, costText: cost + '⚒️', state: state, lockText: lockText,
        builtBy: builtBy === undefined ? -1 : builtBy,
        effect: yieldText(w.yields) + (w.protect ? ' · 免疫蛮族' : '') + ' · +' + SCORE.wonder + '分' };
    });
    var era = eraOf(p);
    var techs = TECHS.map(function (t) {
      var state, lockText = '';
      if (has(p.techs, t.id)) state = 'done';
      else if (t.era > era) { state = 'locked'; lockText = ERAS[t.era]; }
      else state = legalIds['research:' + t.id] ? 'ok' : 'poor';
      var cost = techCost(game, pi, t);
      return { id: t.id, name: t.name, icon: t.icon, cost: cost, costText: cost + '🔬', state: state, lockText: lockText,
        effect: t.effect, era: t.era, eraName: ERAS[t.era] };
    });

    if (p.techs.length >= TECHS.length) {
      techs.push({ id: FUTURE.id, name: FUTURE.name, icon: FUTURE.icon, cost: FUTURE.cost, costText: FUTURE.cost + '🔬',
        state: legalIds['future:' + FUTURE.id] ? 'ok' : 'poor', lockText: '', repeat: true, effect: '+' + FUTURE.gain + '🎭 · ' + FUTURE.effect, era: 4, eraName: ERAS[4] });
    }
    var claimableCount = 0, affordableClaim = 0;
    for (i = 0; i < tiles.length; i++) { if (tiles[i].claimable) claimableCount++; if (tiles[i].affordable) affordableClaim++; }
    var canDoCard = legal.some(function (a) { return a.type !== 'expand' && a.type !== 'festival'; });
    var hint;
    if (game.phase === 'over') hint = '对局结束';
    else if (!humanTurn) hint = '其他文明行动中…';
    else if (actionsLeft(game) <= 0) hint = '本回合行动已用完，点「结束回合」';
    else if (affordableClaim > 0 && canDoCard) hint = '点击发亮的格子扩张，或在下方建造 / 研究';
    else if (affordableClaim > 0) hint = '点击发亮的格子扩张领土';
    else if (canDoCard) hint = '下方有可以建造或研究的项目';
    else if (claimableCount > 0) hint = '资源暂时不够，结束回合积累一下吧';
    else hint = '周围已无空地，专心发展内政吧';

    var pending = game.pendingEvent ? byId(EVENTS, game.pendingEvent.id) : null;
    var players = game.players.map(function (_, i2) { return playerView(game, i2); });
    var ranking = players.slice().sort(function (a, b) { return b.score - a.score; });

    return {
      round: game.round, maxRound: game.maxRound, phase: game.phase, cur: pi, turnNo: game.turnNo,
      isHumanTurn: humanTurn, mode: game.mode, seed: game.seed, difficulty: game.difficulty,
      humanCount: game.players.filter(function (x) { return x.isHuman; }).length,
      players: players, ranking: ranking, winner: game.winner,
      actionsLeft: game.phase === 'playing' ? actionsLeft(game) : 0, actionsPerTurn: ACTIONS_PER_TURN,
      me: {
        idx: pi, name: p.name, civName: civ.name, icon: civ.icon, color: civ.color, bonus: civ.bonus,
        res: { F: p.res.F, P: p.res.P, S: p.res.S, C: p.culture }, income: p.income,
        era: era, eraName: ERAS[era], score: computeScore(game, pi), tiles: countTiles(game, pi),
        techsDone: p.techs.length, techsInEra: p.techs.length % TECHS_PER_ERA, techsPerEra: TECHS_PER_ERA,
        wonders: p.wonders.map(function (id) { return byId(WONDERS, id).name; })
      },
      board: { w: W, h: H, tiles: tiles },
      buildings: buildings, wonders: wonders, techs: techs,
      log: game.log.slice(-14).reverse().map(function (e) {
        var who = e.p >= 0 ? game.players[e.p] : null;
        return { round: e.r, who: who ? who.name : '', icon: who ? byId(CIVS, who.civ).icon : '📜', color: who ? byId(CIVS, who.civ).color : '', text: e.t, isMe: e.p === pi };
      }),
      pendingEvent: pending ? { id: pending.id, name: pending.name, icon: pending.icon, text: pending.text, round: game.pendingEvent.round } : null,
      hint: hint
    };
  }

  function tileInfo(game, idx) {
    var t = game.tiles[idx], terr = TERRAINS[t.t];
    var owner = t.o >= 0 ? game.players[t.o] : null;
    var lines = [];
    if (t.cap) lines.push(owner.name + '的首都');
    else lines.push(terr.name + (owner ? '（' + owner.name + '）' : '（无主）'));
    lines.push('产出 ' + (yieldText(t.o >= 0 ? tileYield(game, t.o, t) : (t.cap ? CAPITAL_YIELD : terr.yields)) || '无'));
    if (terr.needTech) lines.push('需研究「' + byId(TECHS, terr.needTech).name + '」才能占领');
    if (terr.bonus) lines.push(t.looted ? '遗迹已被探索' : '首次占领可获得一份随机奖励');
    if (t.t === 'natwonder') lines.push('每回合额外 +1🎭');
    return { title: lines[0], lines: lines.slice(1), icon: t.cap ? byId(CIVS, owner.civ).icon : terr.icon };
  }

  // ------------------------------------------------------------
  // 存档
  // ------------------------------------------------------------
  function serialize(game) { return JSON.stringify(game); }
  function load(json) {
    var g = typeof json === 'string' ? JSON.parse(json) : json;
    if (!g || g.v !== 1 || !g.tiles || !g.players) throw new Error('存档格式不正确');
    return g;
  }

  return {
    W: W, H: H, MAX_ROUND: MAX_ROUND, EVENT_EVERY: EVENT_EVERY, ACTIONS_PER_TURN: ACTIONS_PER_TURN, SCORE: SCORE,
    RES: RES, FESTIVAL: FESTIVAL, FUTURE: FUTURE, TERRAINS: TERRAINS, CIVS: CIVS, ERAS: ERAS, TECHS: TECHS, BUILDINGS: BUILDINGS, WONDERS: WONDERS, EVENTS: EVENTS,
    createGame: createGame, dailySeed: dailySeed,
    getView: getView, tileInfo: tileInfo, getLegalActions: getLegalActions,
    applyAction: applyAction, endTurn: endTurn, ackEvent: ackEvent,
    computeIncome: computeIncome, computeScore: computeScore, expandCost: expandCost, buildCost: buildCost, techCost: techCost, eraOf: eraOf,
    serialize: serialize, load: load
  };
});
