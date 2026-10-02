// 本地存档（wx.storage 的薄封装，所有读写都包了 try/catch）
const E = require('../engine/civ-engine.js');
const SAVE = 'civ-board/save', META = 'civ-board/meta', PREFIX = 'civ-board/';

function get(key) { try { return wx.getStorageSync(PREFIX + key) || ''; } catch (e) { return ''; } }
function set(key, val) { try { wx.setStorageSync(PREFIX + key, val); } catch (e) { /* ignore */ } }
function del(key) { try { wx.removeStorageSync(PREFIX + key); } catch (e) { /* ignore */ } }

function loadGame() {
  try { const s = wx.getStorageSync(SAVE); return s ? E.load(s) : null; } catch (e) { return null; }
}
function saveGame(game) { try { wx.setStorageSync(SAVE, E.serialize(game)); } catch (e) { /* ignore */ } }
function clearGame() { try { wx.removeStorageSync(SAVE); wx.removeStorageSync(META); } catch (e) { /* ignore */ } }
function getMeta() { try { return JSON.parse(wx.getStorageSync(META) || '{}'); } catch (e) { return {}; } }
function setMeta(meta) { try { wx.setStorageSync(META, JSON.stringify(meta)); } catch (e) { /* ignore */ } }

module.exports = { get, set, del, loadGame, saveGame, clearGame, getMeta, setMeta };
