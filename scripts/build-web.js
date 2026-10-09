// 把网页版打包成单文件：dist/civ-board.html（可直接双击打开）和 dist/civ-board.artifact.html（无文档骨架，用于托管发布）
'use strict';
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(root, f), 'utf8');
const html = read('web/index.html'), css = read('web/style.css'), engine = read('miniprogram/engine/civ-engine.js'), app = read('web/app.js');
const body = html.split('<!-- BODY START -->')[1].split('<!-- BODY END -->')[0].replace(/<script src="[^"]+"><\/script>\s*/g, '').trim();
const font = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=ZCOOL+XiaoWei&display=swap">';
const scripts = '<script>\n' + engine + '\n</script>\n<script>\n' + app + '\n</script>';
const fragment = '<title>文明小桌</title>\n' + font + '\n<style>\n' + css + '\n</style>\n' + body + '\n' + scripts + '\n';
const standalone = '<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' +
  '<title>文明小桌</title>\n' + font + '\n<style>\n' + css + '\n</style>\n</head>\n<body>\n' + body + '\n' + scripts + '\n</body>\n</html>\n';
fs.mkdirSync(path.join(root, 'dist'), { recursive: true });
fs.writeFileSync(path.join(root, 'dist/civ-board.html'), standalone);
fs.writeFileSync(path.join(root, 'dist/civ-board.artifact.html'), fragment);
console.log('已生成 dist/civ-board.html (' + (standalone.length / 1024).toFixed(0) + ' KB) 与 dist/civ-board.artifact.html');
