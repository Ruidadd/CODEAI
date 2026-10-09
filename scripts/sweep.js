// 参数扫描：复制引擎到临时文件改常量，各跑 150 局，比较结果
'use strict';
const fs = require('fs'), path = require('path'), os = require('os');
const src = fs.readFileSync(path.join(__dirname, '../miniprogram/engine/civ-engine.js'), 'utf8');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'civ-sweep-'));
function variant(name, edits) {
  let s = src;
  for (const [a, b] of edits) { if (!s.includes(a)) throw new Error('缺少片段 ' + a); s = s.replace(a, b); }
  const f = path.join(tmp, name + '.js'); fs.writeFileSync(f, s); return require(f);
}
function run(E, N = 150) {
  let tiles = 0, techs = 0, bld = 0, wonders = 0, culture = 0, score = 0, n = 0, unclaimed = 0, spread = 0, idle = 0, turns = 0;
  const civWins = {};
  for (let seed = 1; seed <= N; seed++) {
    const ids = E.CIVS.map(c => c.id); const start = seed % 6;
    const civs = [0, 1, 2, 3].map(i => ids[(start + i * (1 + seed % 2)) % 6]).filter((v, i, a) => a.indexOf(v) === i).slice(0, 4);
    while (civs.length < 4) civs.push(ids.find(id => !civs.includes(id)));
    const g = E.createGame({ seed, players: civs.map(id => ({ civ: id })) });
    const scores = g.players.map((_, i) => E.computeScore(g, i));
    spread += Math.max(...scores) - Math.min(...scores);
    unclaimed += g.tiles.filter(t => t.o === -1).length;
    // 统计空转回合：日志里没有该玩家动作的回合
    g.players.forEach((p, i) => {
      n++; tiles += g.tiles.filter(t => t.o === i).length; techs += p.techs.length; bld += p.buildings.length; wonders += p.wonders.length; culture += p.culture; score += scores[i];
      civWins[p.civ] = civWins[p.civ] || { n: 0, w: 0 }; civWins[p.civ].n++; if (i === g.winner) civWins[p.civ].w++;
    });
  }
  const f = x => (x / n).toFixed(1);
  const wr = Object.keys(civWins).map(id => `${E.CIVS.find(c => c.id === id).name}${(100 * civWins[id].w / civWins[id].n).toFixed(0)}%`).join(' ');
  return `领土${f(tiles)} 科技${f(techs)} 建筑${f(bld)} 奇观${f(wonders)} 文化${f(culture)} 总分${f(score)} 空地${(unclaimed / N).toFixed(1)} 分差${(spread / N).toFixed(1)} | ${wr}`;
}
const variants = {
  '当前(3动/二次扩张)': [],
  '2动/二次扩张': [['var ACTIONS_PER_TURN = 3;', 'var ACTIONS_PER_TURN = 2;']],
  '3动/线性扩张': [['var EXPAND_QUAD = 10;', 'var EXPAND_QUAD = 100000;']],
  '2动/线性扩张': [['var ACTIONS_PER_TURN = 3;', 'var ACTIONS_PER_TURN = 2;'], ['var EXPAND_QUAD = 10;', 'var EXPAND_QUAD = 100000;']],
  '3动/二次缓(16)': [['var EXPAND_QUAD = 10;', 'var EXPAND_QUAD = 16;']],
  '2动/二次缓(16)': [['var ACTIONS_PER_TURN = 3;', 'var ACTIONS_PER_TURN = 2;'], ['var EXPAND_QUAD = 10;', 'var EXPAND_QUAD = 16;']],
};
for (const [name, edits] of Object.entries(variants)) {
  console.log(name.padEnd(16), run(variant(name.replace(/[^\w]/g, '_'), edits)));
}
