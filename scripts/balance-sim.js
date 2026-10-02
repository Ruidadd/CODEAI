// 平衡性模拟：N 局纯电脑对局，输出各项平均值，用来调参数
'use strict';
const E = require('../miniprogram/engine/civ-engine.js');
const N = Number(process.argv[2] || 300);
const civWins = {}, civScore = {};
let tiles = 0, techs = 0, bld = 0, wonders = 0, culture = 0, score = 0, players = 0, unclaimed = 0, spread = 0;
let maxScore = 0, minScore = 1e9;
for (let seed = 1; seed <= N; seed++) {
  const civs = E.CIVS.map(c => c.id).sort(() => (seed * 7919) % 3 - 1).slice(0, 4);
  const g = E.createGame({ seed, players: civs.map(id => ({ civ: id })) });
  const scores = g.players.map((_, i) => E.computeScore(g, i));
  spread += Math.max(...scores) - Math.min(...scores);
  unclaimed += g.tiles.filter(t => t.o === -1).length;
  g.players.forEach((p, i) => {
    players++;
    tiles += g.tiles.filter(t => t.o === i).length;
    techs += p.techs.length; bld += p.buildings.length; wonders += p.wonders.length; culture += p.culture; score += scores[i];
    maxScore = Math.max(maxScore, scores[i]); minScore = Math.min(minScore, scores[i]);
    civScore[p.civ] = (civScore[p.civ] || 0) + scores[i];
    civWins[p.civ] = civWins[p.civ] || { n: 0, w: 0 };
    civWins[p.civ].n++;
    if (i === g.winner) civWins[p.civ].w++;
  });
}
const f = x => (x / players).toFixed(1);
console.log(`局数 ${N}，每局 4 人，20 回合`);
console.log(`平均 领土 ${f(tiles)} | 科技 ${f(techs)}/12 | 建筑 ${f(bld)}/13 | 奇观 ${f(wonders)} | 文化 ${f(culture)} | 总分 ${f(score)} (${minScore}~${maxScore})`);
console.log(`平均剩余无主格 ${(unclaimed / N).toFixed(1)}/64，一二名分差均值 ${(spread / N).toFixed(1)}`);
for (const id of Object.keys(civWins)) {
  const c = E.CIVS.find(c => c.id === id);
  console.log(`  ${c.name}: 胜率 ${(100 * civWins[id].w / civWins[id].n).toFixed(0)}%  均分 ${(civScore[id] / civWins[id].n).toFixed(1)}`);
}
