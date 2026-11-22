/* review-ui.js — 复习站公共交互组件（纯原生 JS，零依赖）
 *
 * 渲染管线约束：
 *   各页面内联脚本按「占位符保护 $$/$ → marked.parse() → 还原公式 → renderMathInElement()」执行。
 *   本脚本不触碰该流程，只在 #content 被填充且 renderMathInElement 同步执行完毕之后才挂载组件
 *   （MutationObserver 回调属于微任务，必然晚于内联脚本整个同步流程）。
 *
 * 组件：悬浮控制栏（关键词过滤 / 背诵自测 / 隐藏已掌握）、悬浮目录、考点掌握度（localStorage）。
 */
(function () {
  'use strict';
  if (window.__reviewUI) return;
  window.__reviewUI = true;

  var KEY_MASTERED = 'rui:m:';     // rui:m:<页面路径>::<标题文本>  = "1"
  var KEY_META = 'rui:meta:';      // rui:meta:<页面路径>            = 考点总数（供总目录页读取）
  var KEY_PREF = 'rui:pref:';      // rui:pref:<name>               = 偏好开关
  var root = document.documentElement;

  /* ───────── localStorage 安全封装 ───────── */
  var ls = null;
  try { ls = window.localStorage; ls.setItem('__rui', '1'); ls.removeItem('__rui'); } catch (e) { ls = null; }
  function lget(k) { try { return ls ? ls.getItem(k) : null; } catch (e) { return null; } }
  function lset(k, v) { try { if (ls) ls.setItem(k, v); } catch (e) { /* 配额/隐私模式 */ } }
  function ldel(k) { try { if (ls) ls.removeItem(k); } catch (e) { } }

  var pagePath = location.pathname;
  try { pagePath = decodeURIComponent(pagePath); } catch (e) { }

  /* ───────── 工具 ───────── */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function norm(s) { return s.replace(/\s+/g, ' ').trim(); }
  // 提取标题纯文本：KaTeX 渲染节点 → 其 TeX 源码，保证 key 稳定且无 MathML 重复文本
  function plainText(node) {
    var c = node.cloneNode(true);
    var ks = c.querySelectorAll('.katex');
    for (var i = 0; i < ks.length; i++) {
      var a = ks[i].querySelector('annotation[encoding="application/x-tex"]');
      ks[i].parentNode.replaceChild(document.createTextNode(a ? '$' + a.textContent + '$' : ''), ks[i]);
    }
    return norm(c.textContent);
  }
  function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

  /* ───────── 等待正文渲染完成 ───────── */
  function whenRendered(cb) {
    function start() {
      var c = document.getElementById('content');
      if (!c) return;
      if (c.children.length) { setTimeout(function () { cb(c); }, 0); return; }
      var mo = new MutationObserver(function () {
        if (c.children.length) {
          mo.disconnect();
          setTimeout(function () { cb(c); }, 0);
        }
      });
      mo.observe(c, { childList: true });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
  }

  whenRendered(init);

  function init(content) {
    if (root.getAttribute('data-rui-ready')) return;
    root.setAttribute('data-rui-ready', '1');

    var BLOCK = { UL: 1, OL: 1, P: 1, TABLE: 1, PRE: 1, BLOCKQUOTE: 1, DIV: 1, H1: 1, H2: 1, H3: 1, H4: 1, HR: 1 };

    /* ═════════ 1. 背诵自测遮罩的结构准备（模式关闭时视觉无变化） ═════════ */
    function firstMeaningful(parent) {
      var n = parent.firstChild;
      while (n && n.nodeType === 3 && !n.nodeValue.trim()) n = n.nextSibling;
      return n;
    }
    function hasContent(nodes) {
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n.nodeType === 1 || (n.nodeType === 3 && n.nodeValue.trim())) return true;
      }
      return false;
    }
    function maskSiblingBlocks(start) {
      for (var n = start; n; n = n.nextSibling) {
        if (n.nodeType !== 1 || n.nodeName === 'UL' || n.nodeName === 'OL') continue;
        if (n.nodeName === 'HR') continue;
        n.classList.add('rui-m');
      }
    }
    function maskListItem(li) {
      var host = li;
      var first = firstMeaningful(li);
      if (first && first.nodeName === 'P') { host = first; first = firstMeaningful(host); }
      if (!first || first.nodeName !== 'STRONG') return;

      var n = first.nextSibling;
      // 保留紧随其后的冒号在遮罩外，使“术语：”仍可见
      if (n && n.nodeType === 3) {
        var m = /^\s*[:：]\s*/.exec(n.nodeValue);
        if (m && m[0].length < n.nodeValue.length) n = n.splitText(m[0].length);
        else if (m) n = n.nextSibling;
      }
      var run = [];
      while (n && !(n.nodeType === 1 && BLOCK[n.nodeName])) { run.push(n); n = n.nextSibling; }
      var masked = false;
      if (hasContent(run)) {
        var span = el('span', 'rui-m rui-m-inline');
        run[0].parentNode.insertBefore(span, run[0]);
        for (var i = 0; i < run.length; i++) span.appendChild(run[i]);
        masked = true;
      }
      if (n) { maskSiblingBlocks(n); masked = masked || !!(n.nodeType === 1 && n.nodeName !== 'UL' && n.nodeName !== 'OL'); }
      if (host !== li) maskSiblingBlocks(host.nextSibling);
    }

    var bqs = content.querySelectorAll('blockquote');
    for (var i = 0; i < bqs.length; i++) {
      if (!bqs[i].parentNode.closest('blockquote')) bqs[i].classList.add('rui-m');
    }
    var lis = content.querySelectorAll('li');
    for (i = 0; i < lis.length; i++) {
      if (!lis[i].closest('blockquote')) maskListItem(lis[i]);
    }
    // 折叠答案区：<details> 中除 <summary> 外的内容
    var dets = content.querySelectorAll('details');
    for (i = 0; i < dets.length; i++) {
      var d = dets[i], kids = [], k;
      for (k = d.firstChild; k; k = k.nextSibling) if (k.nodeName !== 'SUMMARY') kids.push(k);
      if (hasContent(kids)) {
        var wrap = el('div', 'rui-m');
        d.insertBefore(wrap, kids[0]);
        for (k = 0; k < kids.length; k++) wrap.appendChild(kids[k]);
      }
    }

    /* ═════════ 2. 标题分节 + 掌握度标签 ═════════ */
    var sections = [];           // 含前言（level 0）、h2、h3
    var curH2 = null, cur = { level: 0, h: null, blocks: [], kids: [], parent: null, text: '', headText: '' };
    sections.push(cur);
    var kidsEls = content.children;
    for (i = 0; i < kidsEls.length; i++) {
      var node = kidsEls[i];
      if (node.nodeName === 'H2' || node.nodeName === 'H3') {
        var lvl = node.nodeName === 'H2' ? 2 : 3;
        var s = { level: lvl, h: node, blocks: [], kids: [], parent: lvl === 3 ? curH2 : null, text: '', headText: '', mastered: false, key: '', tocLink: null };
        if (lvl === 2) curH2 = s; else if (curH2) curH2.kids.push(s);
        sections.push(s);
        cur = s;
      } else {
        cur.blocks.push(node);
      }
    }
    var heads = sections.filter(function (s) { return s.level > 0; });

    var seenKeys = {};
    heads.forEach(function (s, idx) {
      var h = s.h;
      // 将标题原有内容包进 span，再 flex 布局放入右侧状态标签
      var tw = el('span', 'rui-h-text');
      while (h.firstChild) tw.appendChild(h.firstChild);
      h.appendChild(tw);
      h.classList.add('rui-h');
      if (!h.id) h.id = 'rui-h-' + idx;
      s.textEl = tw;

      var text = plainText(tw);
      s.headText = text.toLowerCase();
      var base = KEY_MASTERED + pagePath + '::' + text;
      var n = (seenKeys[base] = (seenKeys[base] || 0) + 1);
      s.key = n > 1 ? base + '#' + n : base;
      s.mastered = lget(s.key) === '1';

      var tag = el('button', 'rui-mastered-tag', '已掌握');
      tag.type = 'button';
      tag.title = '标记 / 取消标记为已掌握';
      tag.setAttribute('aria-pressed', s.mastered ? 'true' : 'false');
      tag.addEventListener('click', function () { setMastered(s, !s.mastered); });
      h.appendChild(tag);
      s.tag = tag;
      h.classList.toggle('rui-done', s.mastered);
    });
    lset(KEY_META + pagePath, String(heads.length));

    // 缓存各节检索文本（标题文本不含“已掌握”标签）
    sections.forEach(function (s) {
      s.blockTexts = s.blocks.map(function (b) { return (b.textContent || '').toLowerCase(); });
      s.text = s.headText + '\n' + s.blockTexts.join('\n');
    });

    /* ═════════ 3. 顶部悬浮控制栏 ═════════ */
    var bar = document.querySelector('.nav-bar');
    var backLink = bar ? bar.querySelector('a') : null;
    if (!bar) {
      bar = el('div', 'nav-bar');
      document.body.insertBefore(bar, document.body.firstChild);
    }
    if (!backLink) {
      backLink = el('a', null, '← 返回复习总目录');
      backLink.href = '../index.html';
    }
    backLink.classList.add('rui-back');
    bar.classList.add('rui-toolbar');
    var row = el('div', 'rui-tb-row');
    row.appendChild(backLink);               // 保留原有返回链接节点

    var searchBox = el('div', 'rui-search');
    var input = el('input');
    input.type = 'search';
    input.placeholder = '过滤关键词（空格分隔多词；按 / 聚焦）';
    input.setAttribute('aria-label', '关键词过滤');
    input.autocomplete = 'off';
    var countEl = el('span', 'rui-count');
    searchBox.appendChild(input);
    searchBox.appendChild(countEl);
    row.appendChild(searchBox);

    function makeSwitch(label, title) {
      var lab = el('label', 'rui-sw');
      lab.title = title || '';
      var cb = el('input');
      cb.type = 'checkbox';
      lab.appendChild(cb);
      lab.appendChild(el('span', 'rui-track'));
      lab.appendChild(el('span', 'rui-lbl', label));
      return { label: lab, input: cb };
    }
    var swOnly = makeSwitch('仅显示匹配章节', '仅保留包含关键词的章节');
    var swRecall = makeSwitch('背诵自测模式', '遮罩释义 / 答案，点击条目揭晓，再点重新遮盖');
    var swHide = makeSwitch('隐藏已掌握考点', '二轮复习：隐藏已标记“已掌握”的章节');
    var sws = el('div', 'rui-switches');
    sws.appendChild(swOnly.label);
    sws.appendChild(swRecall.label);
    sws.appendChild(swHide.label);
    row.appendChild(sws);

    var prog = el('div', 'rui-progress');
    var progText = el('span');
    var progBar = el('span', 'rui-bar');
    var progFill = el('i');
    progBar.appendChild(progFill);
    prog.appendChild(progText);
    prog.appendChild(progBar);
    row.appendChild(prog);

    while (bar.firstChild) bar.removeChild(bar.firstChild);
    bar.appendChild(row);

    function syncBarHeight() { root.style.setProperty('--rui-tb-h', bar.offsetHeight + 'px'); }
    syncBarHeight();
    if (window.ResizeObserver) new ResizeObserver(syncBarHeight).observe(bar);
    else window.addEventListener('resize', syncBarHeight);

    /* ═════════ 4. 悬浮目录 ═════════ */
    var toc = el('aside', 'rui-toc');
    toc.setAttribute('aria-label', '页面目录');
    var tocHead = el('div', 'rui-toc-head');
    tocHead.appendChild(el('span', null, '目录 · ' + heads.length + ' 个考点'));
    var tocClose = el('button', 'rui-toc-close', '✕');
    tocClose.type = 'button';
    tocClose.setAttribute('aria-label', '收起目录');
    tocHead.appendChild(tocClose);
    var tocList = el('nav', 'rui-toc-list');
    heads.forEach(function (s) {
      var a = el('a', s.level === 2 ? 'rui-l2' : 'rui-l3');
      a.href = '#' + s.h.id;
      a.appendChild(s.textEl.cloneNode(true));
      a.addEventListener('click', function (e) {
        e.preventDefault();
        s.h.scrollIntoView({ behavior: prefersReduced() ? 'auto' : 'smooth', block: 'start' });
        try { history.replaceState(null, '', '#' + s.h.id); } catch (err) { }
        if (!desktop.matches) setToc(false);
      });
      tocList.appendChild(a);
      s.tocLink = a;
      a.classList.toggle('rui-toc-done', s.mastered);
    });
    toc.appendChild(tocHead);
    toc.appendChild(tocList);
    var fab = el('button', 'rui-toc-fab', '☰');
    fab.type = 'button';
    fab.title = '目录';
    fab.setAttribute('aria-label', '打开目录');
    document.body.appendChild(toc);
    document.body.appendChild(fab);

    var desktop = window.matchMedia('(min-width: 1180px)');
    function prefersReduced() { return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches; }
    function setToc(on, persist) {
      root.classList.toggle('rui-toc-on', on);
      fab.setAttribute('aria-expanded', on ? 'true' : 'false');
      if (persist && desktop.matches) lset(KEY_PREF + 'toc', on ? '1' : '0');
      if (on) updateSpy();
    }
    function initToc() { setToc(desktop.matches ? lget(KEY_PREF + 'toc') !== '0' : false); }
    tocClose.addEventListener('click', function () { setToc(false, true); });
    fab.addEventListener('click', function () { setToc(true, true); });
    if (desktop.addEventListener) desktop.addEventListener('change', initToc);
    else if (desktop.addListener) desktop.addListener(initToc);

    // 滚动高亮当前章节
    var spyTicking = false, activeSec = null;
    function updateSpy() {
      spyTicking = false;
      if (!heads.length) return;
      var th = bar.offsetHeight + 36, found = null;
      for (var j = 0; j < heads.length; j++) {
        var hh = heads[j].h;
        if (hh.offsetParent === null && hh.getClientRects().length === 0) continue; // 被隐藏的节
        if (hh.getBoundingClientRect().top <= th) found = heads[j]; else break;
      }
      if (found === activeSec) return;
      if (activeSec && activeSec.tocLink) activeSec.tocLink.classList.remove('rui-active');
      activeSec = found;
      if (found && found.tocLink) {
        var a = found.tocLink;
        a.classList.add('rui-active');
        var top = a.offsetTop, bottom = top + a.offsetHeight;
        if (top < tocList.scrollTop + 8) tocList.scrollTop = Math.max(0, top - 40);
        else if (bottom > tocList.scrollTop + tocList.clientHeight - 8) tocList.scrollTop = bottom - tocList.clientHeight + 40;
      }
    }
    function onScroll() { if (!spyTicking) { spyTicking = true; requestAnimationFrame(updateSpy); } }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);

    /* ═════════ 5. 掌握度 / 进度 ═════════ */
    function updateProgress() {
      var done = heads.filter(function (s) { return s.mastered; }).length;
      progText.textContent = '已掌握 ' + done + '/' + heads.length;
      progFill.style.width = heads.length ? (done * 100 / heads.length) + '%' : '0';
    }
    function setMastered(s, v) {
      s.mastered = v;
      if (v) lset(s.key, '1'); else ldel(s.key);
      s.tag.setAttribute('aria-pressed', v ? 'true' : 'false');
      s.h.classList.toggle('rui-done', v);
      if (s.tocLink) s.tocLink.classList.toggle('rui-toc-done', v);
      updateProgress();
      applyVisibility();
    }

    /* ═════════ 6. 关键词过滤 + 可见性统一计算 ═════════ */
    var terms = [], termRe = null;
    function allIn(text) {
      for (var j = 0; j < terms.length; j++) if (text.indexOf(terms[j]) < 0) return false;
      return true;
    }
    function anyIn(text) {
      for (var j = 0; j < terms.length; j++) if (text.indexOf(terms[j]) >= 0) return true;
      return false;
    }
    function clearMarks() {
      var ms = content.querySelectorAll('mark.rui-mark');
      var parents = [];
      for (var j = 0; j < ms.length; j++) {
        var p = ms[j].parentNode;
        p.replaceChild(document.createTextNode(ms[j].textContent), ms[j]);
        if (parents.indexOf(p) < 0) parents.push(p);
      }
      parents.forEach(function (p) { p.normalize(); });
      var hits = content.querySelectorAll('.rui-hit');
      for (j = 0; j < hits.length; j++) hits[j].classList.remove('rui-hit');
    }
    var MARK_LIMIT = 800;
    function markIn(root0, budget) {
      var walker = document.createTreeWalker(root0, NodeFilter.SHOW_TEXT, {
        acceptNode: function (n) {
          if (!n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
          var p = n.parentNode;
          if (p.closest && p.closest('.katex, .rui-mastered-tag, script, style, mark')) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      });
      var list = [], t;
      while ((t = walker.nextNode())) list.push(t);
      var count = 0;
      for (var j = 0; j < list.length && budget.n > 0; j++) {
        var tn = list[j], txt = tn.nodeValue, m, last = 0, frag = null;
        termRe.lastIndex = 0;
        while ((m = termRe.exec(txt)) && budget.n > 0) {
          if (!m[0]) { termRe.lastIndex++; continue; }
          frag = frag || document.createDocumentFragment();
          if (m.index > last) frag.appendChild(document.createTextNode(txt.slice(last, m.index)));
          frag.appendChild(el('mark', 'rui-mark', m[0]));
          last = m.index + m[0].length;
          budget.n--; count++;
        }
        if (frag) {
          if (last < txt.length) frag.appendChild(document.createTextNode(txt.slice(last)));
          tn.parentNode.replaceChild(frag, tn);
        }
      }
      return count;
    }

    var lastQuery = null;
    function applyVisibility() {
      var q = norm(input.value).toLowerCase();
      var filtering = q.length > 0;
      var only = swOnly.input.checked && filtering;
      var hideM = swHide.input.checked;

      if (q !== lastQuery) {
        lastQuery = q;
        clearMarks();
        terms = filtering ? q.split(' ') : [];
        termRe = filtering ? new RegExp(terms.map(escRe).join('|'), 'gi') : null;
        sections.forEach(function (s) {
          s.own = filtering ? allIn(s.text) : true;
          s.headOwn = filtering ? allIn(s.headText) : false;
        });
        var marks = 0, budget = { n: MARK_LIMIT };
        if (filtering) {
          sections.forEach(function (s) {
            if (s.h && anyIn(s.headText)) s.h.classList.add('rui-hit');
            s.blocks.forEach(function (b, bi) { if (anyIn(s.blockTexts[bi])) b.classList.add('rui-hit'); });
          });
          sections.forEach(function (s) {
            if (budget.n <= 0) return;
            if (!s.own) return;
            if (s.h) marks += markIn(s.textEl, budget);
            s.blocks.forEach(function (b) { if (budget.n > 0) marks += markIn(b, budget); });
          });
        }
        var matched = sections.filter(function (s) { return s.level > 0 && s.own; }).length;
        countEl.textContent = filtering ? (matched + ' 节') : '';
        input.setAttribute('data-marks', String(marks));
      }

      sections.forEach(function (s) {
        if (s.level === 2) {
          s.match = s.own || s.kids.some(function (k) { return k.own; });
        } else if (s.level === 3) {
          s.match = s.own || (s.parent && s.parent.headOwn);
        } else {
          s.match = s.own;
        }
        var masteredHidden = false;
        if (s.level === 2) masteredHidden = s.mastered;
        else if (s.level === 3) masteredHidden = s.mastered || !!(s.parent && s.parent.mastered);
        var visible = !(hideM && masteredHidden) && !(only && !s.match);
        if (s.h) s.h.classList.toggle('rui-hidden', !visible);
        s.blocks.forEach(function (b) { b.classList.toggle('rui-hidden', !visible); });
        if (s.tocLink) s.tocLink.classList.toggle('rui-toc-hidden', !visible);
      });
      onScroll();
    }

    var debounce = null;
    input.addEventListener('input', function () {
      clearTimeout(debounce);
      debounce = setTimeout(applyVisibility, 150);
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { input.value = ''; applyVisibility(); input.blur(); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
      var t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      e.preventDefault();
      input.focus();
    });
    swOnly.input.addEventListener('change', applyVisibility);
    swHide.input.addEventListener('change', function () {
      lset(KEY_PREF + 'hide', swHide.input.checked ? '1' : '0');
      applyVisibility();
    });

    /* ═════════ 7. 背诵自测模式 ═════════ */
    var maskEls = content.querySelectorAll('.rui-m');
    function setRecall(on) {
      document.body.classList.toggle('rui-recall', on);
      root.classList.toggle('rui-recall', on);
      for (var j = 0; j < maskEls.length; j++) {
        var m = maskEls[j];
        m.classList.remove('rui-revealed');
        if (on) { m.setAttribute('tabindex', '0'); m.setAttribute('role', 'button'); m.setAttribute('aria-pressed', 'false'); }
        else { m.removeAttribute('tabindex'); m.removeAttribute('role'); m.removeAttribute('aria-pressed'); }
      }
    }
    function toggleMask(m) {
      var r = m.classList.toggle('rui-revealed');
      m.setAttribute('aria-pressed', r ? 'true' : 'false');
    }
    swRecall.input.addEventListener('change', function () {
      lset(KEY_PREF + 'recall', swRecall.input.checked ? '1' : '0');
      setRecall(swRecall.input.checked);
    });
    content.addEventListener('click', function (e) {
      if (!root.classList.contains('rui-recall')) return;
      var m = e.target.closest ? e.target.closest('.rui-m') : null;
      if (!m || !content.contains(m)) return;
      if (window.getSelection && String(window.getSelection()).length) return; // 正在选取文字时不切换
      if (m.classList.contains('rui-revealed') && e.target.closest('a')) return;
      e.preventDefault();
      toggleMask(m);
    });
    content.addEventListener('keydown', function (e) {
      if (!root.classList.contains('rui-recall')) return;
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var m = e.target.classList && e.target.classList.contains('rui-m') ? e.target : null;
      if (!m) return;
      e.preventDefault();
      toggleMask(m);
    });

    /* ═════════ 8. 跨标签页同步 + 初始状态 ═════════ */
    window.addEventListener('storage', function (e) {
      if (!e.key || e.key.indexOf(KEY_MASTERED + pagePath + '::') !== 0) return;
      heads.forEach(function (s) {
        var v = lget(s.key) === '1';
        if (v === s.mastered) return;
        s.mastered = v;
        s.tag.setAttribute('aria-pressed', v ? 'true' : 'false');
        s.h.classList.toggle('rui-done', v);
        if (s.tocLink) s.tocLink.classList.toggle('rui-toc-done', v);
      });
      updateProgress();
      applyVisibility();
    });

    swHide.input.checked = lget(KEY_PREF + 'hide') === '1';
    swRecall.input.checked = lget(KEY_PREF + 'recall') === '1';
    setRecall(swRecall.input.checked);
    initToc();
    updateProgress();
    applyVisibility();

    // 目录锚点（如分享的 #hash）在组件挂载后重新定位
    if (location.hash.length > 1) {
      var target = null;
      try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (e) { }
      if (target) setTimeout(function () { target.scrollIntoView(); }, 0);
    }
  }
})();
