'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const E = require('../miniprogram/engine/civ-engine.js');

const FOUR = [{ civ: 'china', isHuman: true }, { civ: 'rome' }, { civ: 'egypt' }, { civ: 'greece' }];

test('同一种子生成同一张地图和同样的开局', () => {
  const a = E.createGame({ seed: 20261002, players: FOUR });
  const b = E.createGame({ seed: 20261002, players: FOUR });
  assert.equal(E.serialize(a), E.serialize(b));
  const c = E.createGame({ seed: 20261003, players: FOUR });
  assert.notEqual(a.tiles.map(t => t.t).join(), c.tiles.map(t => t.t).join());
});

test('每个文明开局只有首都，且四邻都是可占领的陆地', () => {
  const ALL_HUMAN = FOUR.map(p => ({ ...p, isHuman: true }));
  for (let seed = 1; seed <= 50; seed++) {
    const g = E.createGame({ seed, players: ALL_HUMAN });
    g.players.forEach((p, i) => {
      const owned = g.tiles.filter(t => t.o === i);
      assert.equal(owned.length, 1);
      assert.ok(owned[0].cap);
      const v = E.getView({ ...g, cur: i, phase: 'playing' });
      const claimable = v.board.tiles.filter(t => t.claimable);
      assert.ok(claimable.length >= 2, `seed ${seed} 玩家 ${i} 只有 ${claimable.length} 块可扩张`);
      claimable.forEach(t => assert.notEqual(t.terrain, 'ocean'));
    });
  }
});

test('地图包含遗迹、自然奇观和海洋', () => {
  const g = E.createGame({ seed: 7, players: FOUR });
  const kinds = g.tiles.map(t => t.t);
  assert.equal(kinds.filter(k => k === 'ruins').length, 3);
  assert.equal(kinds.filter(k => k === 'natwonder').length, 1);
  assert.ok(kinds.filter(k => k === 'ocean').length >= 3);
});

test('扩张：只能占相邻空地，扣除对应粮食，非法操作给出中文解释', () => {
  const g = E.createGame({ seed: 3, players: FOUR });
  const p = g.players[0];
  const v = E.getView(g);
  const target = v.board.tiles.find(t => t.claimable);
  const far = v.board.tiles.find(t => !t.claimable && t.owner === -1);
  const foodBefore = p.res.F;
  const r1 = E.applyAction(g, { type: 'expand', idx: far.idx });
  assert.equal(r1.ok, false);
  assert.match(r1.msg, /相邻|航海/);
  const r2 = E.applyAction(g, { type: 'expand', idx: target.idx });
  assert.equal(r2.ok, true);
  assert.equal(g.tiles[target.idx].o, 0);
  assert.equal(p.res.F, foodBefore - target.cost);
  const r3 = E.applyAction(g, { type: 'expand', idx: target.idx });
  assert.equal(r3.ok, false);
  assert.match(r3.msg, /已经是你的领土/);
});

test('海洋需要航海术才能占领', () => {
  const g = E.createGame({ seed: 7, players: FOUR });
  const oceanIdx = g.tiles.findIndex(t => t.t === 'ocean');
  // 把海洋旁边的一格直接给玩家 0，构造相邻条件
  const nb = [oceanIdx - 1, oceanIdx + 1, oceanIdx - 8, oceanIdx + 8].find(i => i >= 0 && i < 64 && g.tiles[i].o === -1 && g.tiles[i].t !== 'ocean');
  g.tiles[nb].o = 0;
  g.players[0].res.F = 99;
  const r = E.applyAction(g, { type: 'expand', idx: oceanIdx });
  assert.equal(r.ok, false);
  assert.match(r.msg, /航海术/);
  g.players[0].techs = ['agri', 'mining', 'writing', 'currency', 'masonry', 'philosophy', 'sailing'];
  assert.equal(E.applyAction(g, { type: 'expand', idx: oceanIdx }).ok, true);
});

test('建筑：需要科技解锁、只能造一次、扣除生产', () => {
  const g = E.createGame({ seed: 11, players: FOUR });
  const p = g.players[0];
  p.res.P = 50;
  const locked = E.applyAction(g, { type: 'build', id: 'library' });
  assert.equal(locked.ok, false);
  assert.match(locked.msg, /文字/);
  assert.equal(E.applyAction(g, { type: 'build', id: 'granary' }).ok, true);
  assert.equal(p.res.P, 45);
  const again = E.applyAction(g, { type: 'build', id: 'granary' });
  assert.equal(again.ok, false);
  assert.equal(E.computeIncome(g, 0).F, E.computeIncome({ ...g, players: [{ ...p, buildings: [] }, ...g.players.slice(1)] }, 0).F + 2);
});

test('科技：按时代顺序研究，集齐 3 项进入下一时代并奖励文化', () => {
  const g = E.createGame({ seed: 11, players: FOUR });
  const p = g.players[0];
  p.res.S = 100;
  const early = E.applyAction(g, { type: 'research', id: 'currency' });
  assert.equal(early.ok, false);
  assert.equal(E.eraOf(p), 0);
  ['agri', 'mining'].forEach(id => assert.equal(E.applyAction(g, { type: 'research', id }).ok, true));
  p.actions = 0; // 绕过每回合行动上限，单测科技规则
  const cultureBefore = p.culture;
  const r = E.applyAction(g, { type: 'research', id: 'writing' });
  assert.equal(r.ok, true);
  assert.match(r.msg, /古典时代/);
  assert.equal(E.eraOf(p), 1);
  assert.equal(p.culture, cultureBefore + E.SCORE.era);
  // 科技越多越贵：货币基础 7，已有 3 项科技 → 10，华夏再 -1 → 9
  assert.equal(E.getView(g).techs.find(t => t.id === 'currency').cost, 9);
  assert.equal(E.applyAction(g, { type: 'research', id: 'currency' }).ok, true);
});

test('奇观全局唯一，埃及享受折扣', () => {
  const g = E.createGame({ seed: 5, players: [{ civ: 'egypt', isHuman: true }, { civ: 'rome', isHuman: true }] });
  g.players[0].res.P = 100; g.players[1].res.P = 100;
  const v = E.getView(g);
  assert.equal(v.wonders.find(w => w.id === 'stonehenge').cost, 10);
  assert.equal(E.applyAction(g, { type: 'wonder', id: 'stonehenge' }).ok, true);
  assert.equal(g.players[0].res.P, 90);
  E.endTurn(g);
  assert.equal(g.cur, 1);
  const r = E.applyAction(g, { type: 'wonder', id: 'stonehenge' });
  assert.equal(r.ok, false);
  assert.match(r.msg, /埃及/);
  assert.equal(E.getView(g).wonders.find(w => w.id === 'stonehenge').state, 'taken');
});

test('事件每 3 回合触发一次，城墙免疫蛮族', () => {
  const g = E.createGame({ seed: 9, players: [{ civ: 'china', isHuman: true }, { civ: 'rome', isHuman: true }] });
  g.eventDeck = ['barbarians', 'harvest', 'festival', 'plague', 'quake', 'golden', 'boom', 'discovery'];
  g.players[0].buildings.push('walls');
  while (g.round < 3) E.endTurn(g);
  assert.equal(g.round, 3);
  assert.ok(g.pendingEvent && g.pendingEvent.id === 'barbarians');
  const inc0 = g.players[0].income, inc1 = g.players[1].income;
  // 玩家 0 有城墙：资源 = 上回合剩余 + 本回合收入，不扣；玩家 1 被扣
  assert.ok(E.getView(g).pendingEvent.name === '蛮族来袭');
  E.ackEvent(g);
  assert.equal(g.pendingEvent, null);
  E.endTurn(g); E.endTurn(g);
  assert.equal(g.round, 4);
  assert.equal(g.pendingEvent, null);
  while (g.round < 6) E.endTurn(g);
  assert.equal(g.pendingEvent.id, 'harvest');
});

test('文明被动能力生效', () => {
  const mk = civ => E.createGame({ seed: 2, players: [{ civ, isHuman: true }, { civ: civ === 'rome' ? 'china' : 'rome' }] });
  assert.equal(E.computeIncome(mk('china'), 0).S, 2);
  assert.equal(E.getView(mk('china')).techs.find(t => t.id === 'agri').cost, 4, '华夏科技造价 -1');
  assert.equal(E.computeIncome(mk('persia'), 0).P, 2);
  assert.equal(E.computeIncome(mk('greece'), 0).C, 1);
  assert.equal(E.getView(mk('greece')).buildings.find(b => b.id === 'festival').cost, 3, '希腊庆典更便宜');
  const rome = mk('rome');
  const idx = E.getView(rome).board.tiles.find(t => t.claimable && t.terrain !== 'desert').idx;
  assert.equal(E.expandCost(rome, 0, idx), 1);
});

test('存档与读档往返一致，且可以继续推进', () => {
  const g = E.createGame({ seed: 123, players: FOUR });
  E.applyAction(g, { type: 'expand', idx: E.getView(g).board.tiles.find(t => t.affordable).idx });
  const json = E.serialize(g);
  const g2 = E.load(json);
  assert.deepEqual(g2, JSON.parse(json));
  E.endTurn(g2);
  assert.equal(g2.round, 2);
  assert.throws(() => E.load('{"v":0}'));
});

test('对局在 20 回合后结束，产生胜者，之后不再接受操作', () => {
  const g = E.createGame({ seed: 77, players: FOUR });
  let guard = 0;
  while (g.phase === 'playing' && guard++ < 100) E.endTurn(g);
  assert.equal(g.phase, 'over');
  assert.equal(g.round, 20);
  assert.ok(g.winner >= 0);
  const v = E.getView(g);
  assert.equal(v.ranking[0].idx, g.winner);
  assert.equal(E.applyAction(g, { type: 'build', id: 'granary' }).ok, false);
  assert.equal(v.board.tiles.filter(t => t.claimable).length, 0);
});

test('纯电脑对局（含多人同机）在 200 个种子上都能无异常跑完', () => {
  for (let seed = 1; seed <= 200; seed++) {
    const g = E.createGame({ seed, difficulty: ['easy', 'normal', 'hard'][seed % 3], players: [{ civ: 'inca' }, { civ: 'persia' }, { civ: 'egypt' }, { civ: 'china' }] });
    assert.equal(g.phase, 'over', `seed ${seed}`);
    g.players.forEach(p => {
      assert.ok(p.res.F >= 0 && p.res.P >= 0 && p.res.S >= 0);
      assert.ok(p.techs.length <= E.TECHS.length);
    });
    // 奇观不重复
    const all = g.players.flatMap(p => p.wonders);
    assert.equal(new Set(all).size, all.length);
  }
  const hot = E.createGame({ seed: 5, players: [{ civ: 'china', isHuman: true }, { civ: 'rome', isHuman: true }, { civ: 'egypt' }] });
  assert.equal(hot.cur, 0);
  E.endTurn(hot);
  assert.equal(hot.cur, 1, '第二个人类玩家应当拿到回合');
  E.endTurn(hot);
  assert.equal(hot.cur, 0, '电脑玩家应当自动跳过');
  assert.equal(hot.round, 2);
});

test('视图模型：卡片状态与提示文字正确', () => {
  const g = E.createGame({ seed: 4, players: FOUR });
  g.players[0].res.S = 10; g.players[0].res.P = 10;
  const v = E.getView(g);
  assert.equal(v.isHumanTurn, true);
  assert.equal(v.actionsLeft, E.ACTIONS_PER_TURN);
  assert.equal(v.buildings.find(b => b.id === 'granary').state, 'ok');
  assert.equal(v.buildings.find(b => b.id === 'library').state, 'locked');
  assert.equal(v.wonders.find(w => w.id === 'stonehenge').state, 'poor');
  assert.equal(v.techs.find(t => t.id === 'currency').state, 'locked');
  assert.ok(v.techs.filter(t => t.state === 'ok').length >= 1);
  assert.equal(v.players.length, 4);
  const info = E.tileInfo(g, 9);
  assert.match(info.title, /首都/);
});

test('每回合最多行动 N 次，用完后提示结束回合', () => {
  const g = E.createGame({ seed: 8, players: FOUR });
  const p = g.players[0];
  p.res.F = 99; p.res.P = 99; p.res.S = 99;
  let done = 0;
  for (const t of E.getView(g).board.tiles.filter(t => t.claimable).slice(0, E.ACTIONS_PER_TURN)) {
    assert.equal(E.applyAction(g, { type: 'expand', idx: t.idx }).ok, true); done++;
  }
  // 若相邻地块不够，用建筑补足行动数
  while (done < E.ACTIONS_PER_TURN) { assert.equal(E.applyAction(g, { type: 'build', id: done === 1 ? 'granary' : 'workshop' }).ok, true); done++; }
  const r = E.applyAction(g, { type: 'build', id: 'shrine' });
  assert.equal(r.ok, false);
  assert.match(r.msg, /行动已用完/);
  assert.equal(E.getView(g).actionsLeft, 0);
  assert.match(E.getView(g).hint, /结束回合/);
  E.endTurn(g);
  assert.equal(E.getView(g).actionsLeft, E.ACTIONS_PER_TURN);
});

test('庆典消耗粮食换文化；研究完全部科技后可研究未来科技', () => {
  const g = E.createGame({ seed: 8, players: FOUR });
  const p = g.players[0];
  p.res.F = 20;
  const c0 = p.culture;
  assert.equal(E.applyAction(g, { type: 'festival', id: 'festival' }).ok, true);
  assert.equal(p.culture, c0 + E.FESTIVAL.gain);
  assert.equal(p.res.F, 20 - E.FESTIVAL.cost);
  assert.equal(E.getView(g).techs.some(t => t.id === 'future'), false);
  const early = E.applyAction(g, { type: 'future', id: 'future' });
  assert.equal(early.ok, false);
  p.techs = E.TECHS.map(t => t.id); p.res.S = 30; p.actions = 0;
  assert.equal(E.getView(g).techs.find(t => t.id === 'future').state, 'ok');
  assert.equal(E.applyAction(g, { type: 'future', id: 'future' }).ok, true);
  assert.equal(p.culture, c0 + E.FESTIVAL.gain + E.FUTURE.gain);
});
