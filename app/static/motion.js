/**
 * CORE OS — Motion Design System
 * ══════════════════════════════════════════════════════════════════
 * Pure vanilla JS. No external dependencies.
 *
 * SYSTEMS:
 *   01. initScrollReveal       — IntersectionObserver fade-up / scale-in
 *   02. initTilt               — 3D card tilt with shine blob
 *   03. initCursor             — smooth dot + lagging ring
 *   04. initParallax           — hero element layer drift
 *   05. initNavIndicator       — sliding active pill
 *   06. initCarousels          — infinite RAF loops
 *   07. initEntrance           — first-paint zoom stagger
 *   08. initProgressBars       — delayed fill transitions
 *   09. initRipple             — click burst
 *   10. initSidebarStagger     — nav item slide-in
 *   11. initStatPulse          — entry value pop
 *   12. initScanline           — breathing opacity
 *   13. initParticleField      — floating ambient canvas particles on dashboard
 *   14. initCursorMagnetic     — buttons attract cursor when nearby
 *   15. initCursorGlowTrail    — radial glow follows cursor through bg
 *   16. initTextScramble       — cyberpunk decode animation on headers
 *   17. initPageTransition     — cinematic flash overlay on navigation
 *   18. initHolographic        — prismatic rainbow shimmer on card hover
 *   19. initDepthLayers        — 3D parallax within each card on tilt
 *   20. initChoreography       — section-level animation timing sequences
 *   21. initNoiseOverlay       — film-grain texture (SVG filter)
 *   22. initFormGlow           — input focus rings and label micro-interactions
 *   23. initTerminalBlink      — cursor blink on hero headings
 */

(function (root) {
  'use strict';

  /* ──────────────────────────────────────────────────────────────────────────
     FEATURE DETECTION
  ────────────────────────────────────────────────────────────────────────── */
  const PRM   = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const TOUCH = ('ontouchstart' in root) || (navigator.maxTouchPoints > 0);
  const SLOW  = navigator.hardwareConcurrency > 0 && navigator.hardwareConcurrency <= 2;

  /* ──────────────────────────────────────────────────────────────────────────
     SHARED UTILITIES
  ────────────────────────────────────────────────────────────────────────── */
  function qsa(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }
  function qs(sel, ctx)  { return (ctx || document).querySelector(sel); }
  function css(id, txt)  {
    if (document.getElementById(id)) return;
    const s = document.createElement('style');
    s.id = id; s.textContent = txt;
    document.head.appendChild(s);
  }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function clamp(v, lo, hi) { return Math.min(Math.max(v, lo), hi); }
  function rand(a, b) { return a + Math.random() * (b - a); }

  /* Global mouse position updated by multiple systems */
  const MOUSE = { x: root.innerWidth / 2, y: root.innerHeight / 2,
                  nx: 0, ny: 0 };  // nx/ny normalised -1..1
  document.addEventListener('mousemove', function (e) {
    MOUSE.x  = e.clientX; MOUSE.y  = e.clientY;
    MOUSE.nx = (e.clientX / root.innerWidth  - .5) * 2;
    MOUSE.ny = (e.clientY / root.innerHeight - .5) * 2;
  }, { passive: true });

  /* ══════════════════════════════════════════════════════════════════════════
     01. SCROLL REVEAL  (unchanged from v1.1)
  ══════════════════════════════════════════════════════════════════════════ */
  function initScrollReveal() {
    css('co-sr', `
      .sr {
        opacity: 0;
        transition:
          opacity  .65s cubic-bezier(.22,1,.36,1),
          transform .65s cubic-bezier(.22,1,.36,1),
          filter   .55s cubic-bezier(.22,1,.36,1);
      }
      .sr-up    { transform: translateY(32px); }
      .sr-scale { transform: scale(.92); filter: blur(6px); }
      .sr-left  { transform: translateX(-28px); }
      .sr-right { transform: translateX(28px); }
      .sr-done  { opacity:1!important; transform:none!important; filter:none!important; }
    `);

    const TARGETS = [
      '.glass-card','.mc','.stat-card','.page-header','.sh',
      '.nba-card','.intel-grid > *','.db-grid-4 > *',
      '.db-grid-3 > *','.db-grid-2 > *','.db-grid-2-1 > *',
    ].join(',');

    qsa(TARGETS).forEach(function (el, i) {
      if (el.closest('#stats-carousel,#achievement-carousel')) return;
      if (el.classList.contains('sr')) return;
      el.classList.add('sr', 'sr-up');
      el.style.transitionDelay = Math.min((i % 7) * 60, 360) + 'ms';
    });

    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('sr-done'); io.unobserve(e.target); }
      });
    }, { threshold: 0.06, rootMargin: '0px 0px -40px 0px' });

    qsa('.sr').forEach(function (el) { io.observe(el); });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     02. 3D CARD TILT  (enhanced: wider perspective range)
  ══════════════════════════════════════════════════════════════════════════ */
  function initTilt() {
    if (TOUCH) return;
    css('co-tilt', `
      .tilt-target { transform-style: flat; will-change: transform; }
      .tilt-shine {
        position:absolute; inset:0; border-radius:inherit;
        pointer-events:none; z-index:3; opacity:0;
        transition: opacity .3s ease;
        background: radial-gradient(
          circle 200px at var(--sx,50%) var(--sy,50%),
          rgba(255,255,255,.08) 0%, transparent 65%);
      }
      .tilt-target:hover .tilt-shine { opacity:1; }
    `);

    const TILT = 9, LIFT = 16;
    function addShine(c) {
      if (!qs('.tilt-shine', c)) { const d = document.createElement('div'); d.className='tilt-shine'; c.appendChild(d); }
    }
    function onMove(e) {
      const r = this.getBoundingClientRect();
      const dx = ((e.clientX-r.left)/r.width -.5)*2;
      const dy = ((e.clientY-r.top) /r.height-.5)*2;
      this.style.transform = `perspective(900px) rotateX(${-dy*TILT}deg) rotateY(${dx*TILT}deg) translateZ(${LIFT}px)`;
      this.style.boxShadow = `0 ${22+dy*10}px ${55+Math.abs(dx)*14}px rgba(0,0,0,.6),0 0 25px rgba(99,102,241,.09)`;
      this.style.setProperty('--sx', ((dx*.5+.5)*100).toFixed(1)+'%');
      this.style.setProperty('--sy', ((dy*.5+.5)*100).toFixed(1)+'%');
    }
    function onLeave() { this.style.transform=''; this.style.boxShadow=''; }

    qsa('.glass-card,.mc').forEach(function (c) {
      c.classList.add('tilt-target'); addShine(c);
      c.addEventListener('pointermove', onMove.bind(c));
      c.addEventListener('pointerleave', onLeave.bind(c));
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     03. CUSTOM CURSOR  (enhanced: trail dots)
  ══════════════════════════════════════════════════════════════════════════ */
  function initCursor() {
    if (TOUCH) return;
    css('co-cur', `
      *:not(input):not(textarea):not(select){cursor:none!important}
      #co-dot,#co-ring{
        position:fixed;top:0;left:0;border-radius:50%;
        pointer-events:none;z-index:999999;
        transform:translate(-50%,-50%);
      }
      #co-dot{
        width:7px;height:7px;
        background:var(--accent2,#22d3ee);
        box-shadow:0 0 10px var(--accent2,#22d3ee),0 0 20px rgba(34,211,238,.4);
        transition:width .12s,height .12s,background .18s;
        will-change:transform;
      }
      #co-ring{
        width:30px;height:30px;
        border:1.5px solid rgba(99,102,241,.55);
        background:transparent;
        transition:width .28s cubic-bezier(.22,1,.36,1),height .28s cubic-bezier(.22,1,.36,1),
                    border-color .28s,opacity .2s;
        will-change:transform;
      }
      .cur-hover #co-dot{width:11px;height:11px;background:#fff;box-shadow:0 0 18px rgba(99,102,241,1),0 0 35px rgba(99,102,241,.5);}
      .cur-hover #co-ring{width:50px;height:50px;border-color:rgba(99,102,241,.85);}
      .cur-click #co-dot{width:5px;height:5px;}
      .cur-click #co-ring{width:20px;height:20px;opacity:.5;}
      .co-trail{
        position:fixed;border-radius:50%;pointer-events:none;z-index:999990;
        background:rgba(99,102,241,.55);
        transform:translate(-50%,-50%);
        will-change:transform,opacity;
      }
    `);

    const dot  = document.createElement('div'); dot.id  = 'co-dot';
    const ring = document.createElement('div'); ring.id = 'co-ring';
    document.body.appendChild(dot); document.body.appendChild(ring);

    /* Trail dots */
    const TRAIL_COUNT = 8;
    const trail = Array.from({length: TRAIL_COUNT}, function (_, i) {
      const d = document.createElement('div');
      d.className = 'co-trail';
      const sz = 5 - i * 0.5;
      d.style.cssText = `width:${sz}px;height:${sz}px;opacity:${0.5 - i*0.055};`;
      document.body.appendChild(d);
      return d;
    });
    const trailPos = trail.map(function () { return { x: -100, y: -100 }; });

    let rx = -200, ry = -200, raf;
    const body = document.body;

    document.addEventListener('mousedown', function(){body.classList.add('cur-click');});
    document.addEventListener('mouseup',   function(){body.classList.remove('cur-click');});

    const HOVER_SEL = 'a,button,[role=button],input,select,textarea,label,.glass-card,.mc,.nav-link,.qa-btn,.sug-item,.nba-card,.ach-badge,.chip,.share-btn-primary,.sug-link,.feedback-fab,.item-card,.buy-btn';
    qsa(HOVER_SEL).forEach(function (el) {
      el.addEventListener('mouseenter', function(){body.classList.add('cur-hover');});
      el.addEventListener('mouseleave', function(){body.classList.remove('cur-hover');});
    });

    function tick() {
      dot.style.transform  = `translate(calc(${MOUSE.x}px - 50%),calc(${MOUSE.y}px - 50%))`;
      rx = lerp(rx, MOUSE.x, .11); ry = lerp(ry, MOUSE.y, .11);
      ring.style.transform = `translate(calc(${rx}px - 50%),calc(${ry}px - 50%))`;

      /* Cascade trail positions */
      for (let i = trail.length - 1; i > 0; i--) {
        trailPos[i].x = lerp(trailPos[i].x, trailPos[i-1].x, .35);
        trailPos[i].y = lerp(trailPos[i].y, trailPos[i-1].y, .35);
      }
      trailPos[0].x = lerp(trailPos[0].x, MOUSE.x, .5);
      trailPos[0].y = lerp(trailPos[0].y, MOUSE.y, .5);
      trail.forEach(function (d, i) {
        d.style.transform = `translate(calc(${trailPos[i].x}px - 50%),calc(${trailPos[i].y}px - 50%))`;
      });

      raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    document.addEventListener('visibilitychange', function () {
      document.hidden ? cancelAnimationFrame(raf) : (raf = requestAnimationFrame(tick));
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     04. PARALLAX  (more layers, stronger effect)
  ══════════════════════════════════════════════════════════════════════════ */
  function initParallax() {
    if (TOUCH) return;
    const LAYERS = [
      { sel:'.page-header h1',      rate:.14 },
      { sel:'.page-header .greeting',rate:.09 },
      { sel:'.identity-badge',       rate:.07 },
      { sel:'.sh',                   rate:.03 },
      { sel:'.login-streak-badge',   rate:.06 },
      { sel:'.threat-score-big',     rate:.05 },
    ];
    const items = [];
    LAYERS.forEach(function (L) {
      qsa(L.sel).forEach(function (el) { items.push({ el: el, rate: L.rate }); });
    });
    if (!items.length) return;

    let ticking = false;
    window.addEventListener('scroll', function () {
      if (ticking) return;
      requestAnimationFrame(function () {
        const sy = window.scrollY;
        items.forEach(function (item) {
          const r = item.el.getBoundingClientRect();
          if (r.bottom < -200 || r.top > root.innerHeight + 200) return;
          item.el.style.transform = `translate3d(0,${sy * item.rate}px,0)`;
        });
        ticking = false;
      });
      ticking = true;
    }, { passive: true });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     05. NAV INDICATOR  (unchanged)
  ══════════════════════════════════════════════════════════════════════════ */
  function initNavIndicator() {
    const nav = qs('.nav-links'), active = nav && qs('.nav-link.active', nav);
    if (!nav || !active) return;
    const pill = document.createElement('div');
    pill.id = 'nav-pill';
    Object.assign(pill.style, {
      position:'absolute', left:'10px', right:'10px', borderRadius:'10px',
      pointerEvents:'none', zIndex:'0',
      background:'rgba(99,102,241,.12)', border:'1px solid rgba(99,102,241,.32)',
      transition:'top .32s cubic-bezier(.22,1,.36,1),height .32s cubic-bezier(.22,1,.36,1)',
      boxShadow:'0 0 18px rgba(99,102,241,.1)',
    });
    nav.style.position = 'relative';
    nav.insertBefore(pill, nav.firstChild);
    function moveTo(el) {
      const nr=nav.getBoundingClientRect(), er=el.getBoundingClientRect();
      pill.style.top=er.top-nr.top+'px'; pill.style.height=er.height+'px';
    }
    moveTo(active);
    qsa('.nav-link',nav).forEach(function(l){ l.style.cssText+='position:relative;z-index:1;'; l.addEventListener('mouseenter',function(){moveTo(l);}); });
    nav.addEventListener('mouseleave',function(){moveTo(active);});
  }

  /* ══════════════════════════════════════════════════════════════════════════
     06. INFINITE CAROUSELS  (unchanged)
  ══════════════════════════════════════════════════════════════════════════ */
  function initCarousels() {
    css('co-car',`.carousel-viewport{overflow:hidden;position:relative;width:100%;}.carousel-track{display:flex;gap:.5rem;width:max-content;will-change:transform;}`);
    ['#stats-carousel','#achievement-carousel'].forEach(function(id) {
      const row = qs(id);
      if (!row) return;
      const children = Array.from(row.children);
      if (children.length < 3) return;
      const vp = document.createElement('div'); vp.className='carousel-viewport';
      const tr = document.createElement('div'); tr.className='carousel-track';
      children.forEach(function(c){ c.style.flexShrink='0'; tr.appendChild(c); });
      Array.from(tr.children).forEach(function(c){ tr.appendChild(c.cloneNode(true)); });
      vp.appendChild(tr); row.parentNode.insertBefore(vp,row); row.remove();
      let pos=0, paused=false;
      const spd = id==='#stats-carousel' ? .4 : .3;
      (function tick(){
        if(!paused){ pos-=spd; if(Math.abs(pos)>=tr.scrollWidth/2) pos=0; tr.style.transform=`translateX(${pos}px)`; }
        requestAnimationFrame(tick);
      })();
      vp.addEventListener('mouseenter',function(){paused=true;});
      vp.addEventListener('mouseleave',function(){paused=false;});
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     07. ENTRANCE ZOOM  (more dramatic)
  ══════════════════════════════════════════════════════════════════════════ */
  function initEntrance() {
    css('co-ent',`
      @keyframes co-enter{ from{opacity:0;transform:scale(.9) translateY(20px);filter:blur(6px);} to{opacity:1;transform:scale(1) translateY(0);filter:blur(0);} }
      @keyframes co-enter-logo{ from{opacity:0;letter-spacing:24px;filter:blur(4px);} to{opacity:1;filter:blur(0);} }
      .co-enter{animation:co-enter .7s cubic-bezier(.22,1,.36,1) both;}
      .co-enter-logo{animation:co-enter-logo .75s cubic-bezier(.22,1,.36,1) both;}
    `);
    const logo = qs('.sidebar-logo');
    if (logo) logo.classList.add('co-enter-logo');
    ['.page-header','.feedback-banner','.overdue-alert','.nba-card','.qa-grid']
      .map(function(s){return qs(s);}).filter(Boolean).slice(0,4)
      .forEach(function(el,i){ el.classList.add('co-enter'); el.style.animationDelay=(i*95)+'ms'; });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     08. PROGRESS BARS  (unchanged)
  ══════════════════════════════════════════════════════════════════════════ */
  function initProgressBars() {
    qsa('.xp-fill,.goal-fill,.hint-fill,.prod-bar-fill').forEach(function(bar) {
      const target = bar.style.width;
      if (!target || target==='0%') return;
      bar.style.width='0%'; bar.style.transition='none';
      requestAnimationFrame(function(){requestAnimationFrame(function(){
        bar.style.transition='width 1.3s cubic-bezier(.22,1,.36,1)';
        bar.style.width=target;
      });});
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     09. BUTTON RIPPLE  (larger ripple)
  ══════════════════════════════════════════════════════════════════════════ */
  function initRipple() {
    css('co-rip',`.rippable{position:relative;overflow:hidden;}.co-ripple-el{position:absolute;border-radius:50%;background:rgba(255,255,255,.22);transform:scale(0);pointer-events:none;animation:co-ripple .6s cubic-bezier(.22,1,.36,1) forwards;}@keyframes co-ripple{to{transform:scale(5);opacity:0;}}`);
    qsa('button[type=submit],.btn-primary,.buy-btn,.sync-btn,.complete-btn,.qa-btn,.nba-btn,.sug-link,.share-btn-primary,.btn-cyber,.fb-submit,.disconnect-btn').forEach(function(btn){
      btn.classList.add('rippable');
      btn.addEventListener('click',function(e){
        const r=btn.getBoundingClientRect(), sz=Math.max(r.width,r.height);
        const el=document.createElement('span'); el.className='co-ripple-el';
        Object.assign(el.style,{width:sz+'px',height:sz+'px',left:(e.clientX-r.left-sz/2)+'px',top:(e.clientY-r.top-sz/2)+'px'});
        btn.appendChild(el); setTimeout(function(){el.remove();},640);
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     10. SIDEBAR STAGGER  (unchanged)
  ══════════════════════════════════════════════════════════════════════════ */
  function initSidebarStagger() {
    qsa('.nav-link').forEach(function(link,i){
      link.style.opacity='0'; link.style.transform='translateX(-16px)';
      link.style.transition=`opacity .38s ease ${80+i*48}ms,transform .38s cubic-bezier(.22,1,.36,1) ${80+i*48}ms`;
      requestAnimationFrame(function(){requestAnimationFrame(function(){ link.style.opacity='1'; link.style.transform='none'; });});
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     11. STAT PULSE  (unchanged)
  ══════════════════════════════════════════════════════════════════════════ */
  function initStatPulse() {
    css('co-sp',`@keyframes co-val-pop{0%{transform:scale(1);}42%{transform:scale(1.12);}100%{transform:scale(1);}}.val-pop{animation:co-val-pop .44s cubic-bezier(.34,1.56,.64,1);}`);
    const io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if(!e.isIntersecting) return;
        const val = e.target.querySelector('.mc-val,.threat-score-big,.prod-score-num');
        if(val){ val.classList.remove('val-pop'); void val.offsetWidth; val.classList.add('val-pop'); setTimeout(function(){val.classList.remove('val-pop');},500); }
        io.unobserve(e.target);
      });
    },{threshold:.4});
    qsa('.mc,.stat-card').forEach(function(el){io.observe(el);});
  }

  /* ══════════════════════════════════════════════════════════════════════════
     12. SCANLINE BREATHING  (unchanged)
  ══════════════════════════════════════════════════════════════════════════ */
  function initScanline() {
    const sl = qs('.scanline');
    if (!sl || TOUCH) return;
    let dir=1, val=.4;
    (function breathe(){ val+=dir*.001; if(val>.7) dir=-1; if(val<.3) dir=1; sl.style.opacity=val.toFixed(4); requestAnimationFrame(breathe); })();
  }

  /* ══════════════════════════════════════════════════════════════════════════
     13. AMBIENT PARTICLE FIELD
     Canvas overlay behind main content. Floating cyan/indigo particles.
  ══════════════════════════════════════════════════════════════════════════ */
  function initParticleField() {
    const main = qs('.main-content');
    if (!main) return;

    const canvas = document.createElement('canvas');
    canvas.id = 'co-particles';
    Object.assign(canvas.style, {
      position:'fixed', top:'0', left:'0',
      width:'100%', height:'100%',
      pointerEvents:'none', zIndex:'0',
      opacity:'.55',
    });
    document.body.insertBefore(canvas, document.body.firstChild);

    const ctx   = canvas.getContext('2d');
    const COUNT = 65;
    let W = canvas.width  = root.innerWidth;
    let H = canvas.height = root.innerHeight;

    const COLORS = ['rgba(99,102,241,X)','rgba(34,211,238,X)','rgba(129,140,248,X)','rgba(16,185,129,X)'];

    const particles = Array.from({length: COUNT}, function () {
      return {
        x:   rand(0, W),
        y:   rand(0, H),
        r:   rand(.6, 2.2),
        vx:  rand(-.18, .18),
        vy:  rand(-.22, -.05),
        col: COLORS[Math.floor(rand(0, COLORS.length))],
        alpha: rand(.25, .7),
        pulse: rand(0, Math.PI*2),
        pspeed: rand(.006, .018),
      };
    });

    function drawFrame() {
      ctx.clearRect(0, 0, W, H);
      particles.forEach(function (p) {
        p.pulse += p.pspeed;
        const a   = p.alpha * (.7 + Math.sin(p.pulse) * .3);
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI*2);
        ctx.fillStyle = p.col.replace('X', a.toFixed(3));
        ctx.fill();

        /* Mouse gravity: very gentle pull toward cursor */
        const dx = MOUSE.x - p.x, dy = MOUSE.y - p.y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < 180) {
          p.vx += (dx / dist) * .003;
          p.vy += (dy / dist) * .003;
        }

        p.x += p.vx; p.y += p.vy;
        /* Speed damping */
        p.vx *= .99; p.vy *= .99;
        /* Wrap */
        if (p.x < -5) p.x = W+5; if (p.x > W+5) p.x = -5;
        if (p.y < -5) p.y = H+5; if (p.y > H+5) p.y = -5;
      });
      requestAnimationFrame(drawFrame);
    }
    requestAnimationFrame(drawFrame);

    window.addEventListener('resize', function () {
      W = canvas.width  = root.innerWidth;
      H = canvas.height = root.innerHeight;
    }, { passive: true });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     14. CURSOR MAGNETIC PULL
     Interactive elements gently attract the cursor when nearby.
  ══════════════════════════════════════════════════════════════════════════ */
  function initCursorMagnetic() {
    if (TOUCH) return;

    const MAG_RANGE = 85;  // px attraction radius
    const MAG_STRENGTH = .28;

    // Apply only to primary action buttons and key cards
    const magnets = qsa('.btn-cyber,.buy-btn,.qa-btn,.nba-btn,.share-btn-primary,.disconnect-btn');

    magnets.forEach(function (el) {
      let animFrame;
      let tx = 0, ty = 0;

      el.addEventListener('mousemove', function (e) {
        cancelAnimationFrame(animFrame);
        const r    = el.getBoundingClientRect();
        const cx   = r.left + r.width  / 2;
        const cy   = r.top  + r.height / 2;
        const dx   = e.clientX - cx;
        const dy   = e.clientY - cy;
        const dist = Math.sqrt(dx*dx + dy*dy);

        if (dist < MAG_RANGE) {
          tx = dx * MAG_STRENGTH;
          ty = dy * MAG_STRENGTH;
          el.style.transform = `translate(${tx}px,${ty}px) scale(1.04)`;
          el.style.transition = 'transform .15s ease, box-shadow .15s ease';
        }
      });

      el.addEventListener('mouseleave', function () {
        /* Spring back */
        let cur = { x: tx, y: ty };
        (function spring() {
          cur.x = lerp(cur.x, 0, .2);
          cur.y = lerp(cur.y, 0, .2);
          el.style.transform = `translate(${cur.x.toFixed(2)}px,${cur.y.toFixed(2)}px)`;
          if (Math.abs(cur.x) > .1 || Math.abs(cur.y) > .1) { animFrame = requestAnimationFrame(spring); }
          else { el.style.transform = ''; el.style.transition = ''; }
        })();
        tx = 0; ty = 0;
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     15. CURSOR GLOW TRAIL THROUGH BACKGROUND
     A soft radial glow follows the cursor, tinting the bg behind cards.
  ══════════════════════════════════════════════════════════════════════════ */
  function initCursorGlowTrail() {
    if (TOUCH) return;

    const glow = document.createElement('div');
    glow.id = 'co-cursor-glow';
    Object.assign(glow.style, {
      position: 'fixed',
      width: '500px', height: '500px',
      borderRadius: '50%',
      background: 'radial-gradient(circle, rgba(99,102,241,.07) 0%, transparent 70%)',
      pointerEvents: 'none',
      zIndex: '1',
      transform: 'translate(-50%,-50%)',
      willChange: 'transform',
      transition: 'opacity .4s ease',
    });
    document.body.appendChild(glow);

    let gx = root.innerWidth/2, gy = root.innerHeight/2;
    (function moveGlow() {
      gx = lerp(gx, MOUSE.x, .055);
      gy = lerp(gy, MOUSE.y, .055);
      glow.style.transform = `translate(calc(${gx}px - 50%),calc(${gy}px - 50%))`;
      requestAnimationFrame(moveGlow);
    })();
  }

  /* ══════════════════════════════════════════════════════════════════════════
     16. TEXT SCRAMBLE / DECODE
     Cyberpunk decode animation: characters scramble then resolve on reveal.
     Applied to page-header h1, sidebar logo, and section headers.
  ══════════════════════════════════════════════════════════════════════════ */
  function initTextScramble() {
    const GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*<>/\\|';
    const SPEED  = 30;   // ms per frame

    function scramble(el) {
      const original = el.textContent;
      const len      = original.length;
      let   frame    = 0;
      const total    = len * 3;  // each char takes 3 frames to resolve

      const interval = setInterval(function () {
        el.textContent = original.split('').map(function (ch, i) {
          if (ch === ' ' || ch === '_') return ch;
          const resolveAt = Math.floor((i / len) * total * .85);
          if (frame >= resolveAt) return ch;
          return GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
        }).join('');

        frame++;
        if (frame > total) { el.textContent = original; clearInterval(interval); }
      }, SPEED);
    }

    // Apply to page header on page load
    const h1 = qs('.page-header h1');
    if (h1) setTimeout(function () { scramble(h1); }, 200);

    // Apply to section headers on scroll-reveal
    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        const tag = e.target.querySelector('.sec-head, .section-header');
        if (tag && !tag.dataset.scrambled) {
          tag.dataset.scrambled = '1';
          scramble(tag);
        }
        io.unobserve(e.target);
      });
    }, { threshold: .3 });

    qsa('.glass-card').forEach(function (el) { io.observe(el); });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     17. CINEMATIC PAGE TRANSITION
     Flash overlay that fires when navigating away via a link/button.
     Creates the illusion of a fast cinematic cut between pages.
  ══════════════════════════════════════════════════════════════════════════ */
  function initPageTransition() {
    css('co-pt',`
      #co-page-flash{
        position:fixed;inset:0;background:rgba(8,14,28,0);
        pointer-events:none;z-index:999998;
        transition:background .18s ease;
      }
      #co-page-flash.co-flash-out{background:rgba(8,14,28,0.7);}
      #co-page-line{
        position:fixed;top:0;left:0;width:0;height:2px;z-index:999999;
        background:linear-gradient(90deg,var(--accent),var(--accent2),var(--success));
        box-shadow:0 0 12px var(--accent2);
        transition:width .35s cubic-bezier(.22,1,.36,1);
        pointer-events:none;
      }
    `);

    const flash = document.createElement('div'); flash.id = 'co-page-flash';
    const line  = document.createElement('div'); line.id  = 'co-page-line';
    document.body.appendChild(flash); document.body.appendChild(line);

    /* Page-load: slide in the progress line */
    requestAnimationFrame(function () {
      line.style.width = '100%';
      setTimeout(function () {
        line.style.transition = 'opacity .3s ease';
        line.style.opacity = '0';
        setTimeout(function () { line.remove(); }, 400);
      }, 500);
    });

    /* Navigation: flash out before leaving */
    document.addEventListener('click', function (e) {
      const anchor = e.target.closest('a[href]');
      if (!anchor) return;
      const href = anchor.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('javascript') ||
          anchor.target === '_blank' || e.ctrlKey || e.metaKey) return;

      e.preventDefault();
      flash.classList.add('co-flash-out');
      setTimeout(function () { root.location.href = href; }, 220);
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     18. HOLOGRAPHIC PRISMATIC CARD EFFECT
     On hover, cards show a rainbow prismatic gradient that tracks mouse.
  ══════════════════════════════════════════════════════════════════════════ */
  function initHolographic() {
    if (TOUCH) return;

    css('co-holo',`
      .holo-active::before {
        content:'';
        position:absolute;inset:0;border-radius:inherit;
        background:conic-gradient(
          from calc(var(--holo-angle,0deg)),
          rgba(255,0,128,.06) 0deg,
          rgba(99,102,241,.08) 60deg,
          rgba(34,211,238,.07) 120deg,
          rgba(16,185,129,.06) 180deg,
          rgba(251,191,36,.07) 240deg,
          rgba(244,63,94,.06) 300deg,
          rgba(255,0,128,.06) 360deg
        );
        pointer-events:none;z-index:2;
        opacity:0;transition:opacity .3s ease;
        mix-blend-mode:screen;
      }
      .holo-active:hover::before { opacity:1; }
    `);

    qsa('.glass-card,.mc').forEach(function (card) {
      card.classList.add('holo-active');
      card.addEventListener('pointermove', function (e) {
        const r   = card.getBoundingClientRect();
        const dx  = e.clientX - r.left - r.width  / 2;
        const dy  = e.clientY - r.top  - r.height / 2;
        const deg = Math.atan2(dy, dx) * (180 / Math.PI);
        card.style.setProperty('--holo-angle', deg + 'deg');
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     19. DEPTH LAYERS IN CARDS
     Card content elements (icon, value, label) move at different Z depths
     during tilt — creates genuine 3D layered depth inside each card.
  ══════════════════════════════════════════════════════════════════════════ */
  function initDepthLayers() {
    if (TOUCH) return;

    css('co-depth',`
      .depth-icon  { transform-style:flat; will-change:transform; transition:transform .18s ease; }
      .depth-val   { transform-style:flat; will-change:transform; transition:transform .18s ease; }
      .depth-label { transform-style:flat; will-change:transform; transition:transform .18s ease; }
    `);

    qsa('.mc, .stat-card').forEach(function (card) {
      /* Tag child elements for depth */
      const icon  = card.querySelector('.mc-icon, .stat-icon');
      const val   = card.querySelector('.mc-val, .stat-val');
      const label = card.querySelector('.mc-lbl, .stat-lbl');
      if (icon)  icon.classList.add('depth-icon');
      if (val)   val.classList.add('depth-val');
      if (label) label.classList.add('depth-label');

      card.addEventListener('pointermove', function (e) {
        const r  = card.getBoundingClientRect();
        const dx = ((e.clientX - r.left) / r.width  - .5);
        const dy = ((e.clientY - r.top)  / r.height - .5);

        /* Each layer moves further in 3D space */
        if (icon)  icon.style.transform  = `translate(${dx*-10}px,${dy*-10}px)`;
        if (val)   val.style.transform   = `translate(${dx*-6}px,${dy*-6}px)`;
        if (label) label.style.transform = `translate(${dx*-2}px,${dy*-2}px)`;
      });

      card.addEventListener('pointerleave', function () {
        if (icon)  icon.style.transform  = '';
        if (val)   val.style.transform   = '';
        if (label) label.style.transform = '';
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     20. SECTION CHOREOGRAPHY
     Each major section has a defined animation sequence that plays when
     it enters the viewport. Think of it as per-section "director's cut".
  ══════════════════════════════════════════════════════════════════════════ */
  function initChoreography() {
    css('co-chor',`
      .choreo-child { opacity:0; transform:translateY(20px); transition:opacity .5s cubic-bezier(.22,1,.36,1),transform .5s cubic-bezier(.22,1,.36,1); }
      .choreo-child.choreo-done { opacity:1; transform:none; }
    `);

    /* Define sequences per container class */
    const SEQUENCES = [
      { container:'.db-grid-4',   children:'> *',        baseDelay:0, step:80  },
      { container:'.db-grid-3',   children:'> *',        baseDelay:0, step:100 },
      { container:'.db-grid-2',   children:'> *',        baseDelay:0, step:120 },
      { container:'.db-grid-2-1', children:'> *',        baseDelay:0, step:120 },
      { container:'.threat-breakdown', children:'.tb-item', baseDelay:200, step:60 },
      { container:'.intel-grid',  children:'> *',        baseDelay:0, step:90  },
    ];

    SEQUENCES.forEach(function (seq) {
      qsa(seq.container).forEach(function (container) {
        qsa(seq.children, container).forEach(function (child, i) {
          child.classList.add('choreo-child');
          child.style.transitionDelay = (seq.baseDelay + i * seq.step) + 'ms';
        });

        const io = new IntersectionObserver(function (entries) {
          entries.forEach(function (e) {
            if (!e.isIntersecting) return;
            qsa('.choreo-child', container).forEach(function (c) { c.classList.add('choreo-done'); });
            io.unobserve(container);
          });
        }, { threshold: .05 });
        io.observe(container);
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     21. NOISE OVERLAY
     Subtle film-grain texture over the entire UI. Pure SVG filter — very cheap.
  ══════════════════════════════════════════════════════════════════════════ */
  function initNoiseOverlay() {
    css('co-noise',`
      body::after {
        content:'';
        position:fixed;inset:0;
        pointer-events:none;
        z-index:99990;
        opacity:.028;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        background-size: 180px 180px;
        animation: co-grain 0.15s steps(1) infinite;
      }
      @keyframes co-grain {
        0%  { background-position: 0 0; }
        10% { background-position: -5% -10%; }
        20% { background-position: -15% 5%; }
        30% { background-position: 7% -25%; }
        40% { background-position: 20% 25%; }
        50% { background-position: -25% 10%; }
        60% { background-position: 15% 5%; }
        70% { background-position: 0 15%; }
        80% { background-position: 25% 35%; }
        90% { background-position: -10% 10%; }
        100%{ background-position: 0 0; }
      }
    `);
  }

  /* ══════════════════════════════════════════════════════════════════════════
     22. FORM GLOW MICRO-INTERACTIONS
     Input focus rings, floating label hints, validation shake.
  ══════════════════════════════════════════════════════════════════════════ */
  function initFormGlow() {
    css('co-form',`
      input:focus, textarea:focus, select:focus {
        outline: none !important;
        border-color: var(--accent) !important;
        box-shadow:
          0 0 0 2px rgba(99,102,241,.18),
          0 0 20px rgba(99,102,241,.12),
          0 0 35px rgba(99,102,241,.06) !important;
        transition: box-shadow .25s ease, border-color .25s ease;
      }
      input:focus ~ label, textarea:focus ~ label {
        color: var(--accent2) !important;
        transform: translateY(-22px) scale(.85) !important;
      }
      .co-shake {
        animation: co-form-shake .35s cubic-bezier(.22,1,.36,1);
      }
      @keyframes co-form-shake {
        0%,100%{ transform:translateX(0); }
        15%    { transform:translateX(-6px); }
        35%    { transform:translateX(5px); }
        55%    { transform:translateX(-4px); }
        75%    { transform:translateX(3px); }
      }
    `);

    /* Shake empty required inputs on invalid submit */
    qsa('form').forEach(function (form) {
      form.addEventListener('submit', function () {
        qsa('input[required],textarea[required]', form).forEach(function (inp) {
          if (!inp.value.trim()) {
            inp.classList.remove('co-shake');
            void inp.offsetWidth;
            inp.classList.add('co-shake');
            setTimeout(function () { inp.classList.remove('co-shake'); }, 400);
          }
        });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════════════════
     23. TERMINAL CURSOR BLINK ON HEADERS
     Adds a blinking terminal cursor after h1 text for cyberpunk feel.
  ══════════════════════════════════════════════════════════════════════════ */
  function initTerminalBlink() {
    css('co-term',`
      .page-header h1::after {
        content: '_';
        animation: co-blink .85s step-start infinite;
        color: var(--accent2);
        margin-left: 2px;
        font-weight: 300;
      }
      @keyframes co-blink {
        0%,100%{ opacity:1; }
        50%    { opacity:0; }
      }
      .sidebar-logo::after {
        content: '▮';
        font-size:.6em;
        animation: co-blink 1.1s step-start infinite;
        color: var(--accent);
        opacity:.6;
        margin-left:3px;
        vertical-align:middle;
      }
    `);
  }

  /* ══════════════════════════════════════════════════════════════════════════
     BOOT SEQUENCE
  ══════════════════════════════════════════════════════════════════════════ */
  function boot() {
    /* === GROUP A: CSS injection (instant, zero runtime cost) === */
    initNoiseOverlay();
    initTerminalBlink();
    initFormGlow();

    /* === GROUP B: CSS class + IntersectionObserver === */
    initScrollReveal();
    initStatPulse();
    initEntrance();
    initChoreography();

    /* === GROUP C: interaction-driven (event listeners) === */
    initNavIndicator();
    initRipple();
    initCarousels();

    /* === GROUP D: RAF-driven (continuous, desktop only) === */
    if (!TOUCH) {
      initTilt();
      initDepthLayers();
      initHolographic();
      initCursor();
      initCursorMagnetic();
      initCursorGlowTrail();
      initParallax();
      initParticleField();
      initScanline();
    }

    /* === GROUP E: one-shot + sequential === */
    initPageTransition();
    initTextScramble();
    initProgressBars();

    requestAnimationFrame(function () {
      requestAnimationFrame(initSidebarStagger);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})(window);


/* ── CORE OS v16: Refined micro-interactions ── */
(function() {
  'use strict';

  // Activity feed item entrance animation
  function animateActivityFeed() {
    var items = document.querySelectorAll('.activity-item');
    items.forEach(function(item, i) {
      item.style.opacity = '0';
      item.style.transform = 'translateX(-12px)';
      item.style.transition = 'opacity 0.35s ease ' + (i * 0.06) + 's, transform 0.35s ease ' + (i * 0.06) + 's';
      setTimeout(function() {
        item.style.opacity = '1';
        item.style.transform = 'translateX(0)';
      }, 100 + i * 60);
    });
  }

  // Quick stats count-up
  function animateQuickStats() {
    var vals = document.querySelectorAll('.qs-val');
    vals.forEach(function(el) {
      var target = parseInt(el.textContent, 10);
      if (isNaN(target) || target === 0) return;
      var start = 0;
      var duration = 800;
      var startTime = performance.now();
      (function step(now) {
        var p = Math.min((now - startTime) / duration, 1);
        var ease = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * ease);
        if (p < 1) requestAnimationFrame(step);
      })(performance.now());
    });
  }

  // Smooth card entrance for activity/summary section
  function revealActivitySection() {
    var section = document.querySelector('.activity-feed');
    if (!section) return;
    var parent = section.closest('.glass-card');
    if (parent) {
      parent.style.opacity = '0';
      parent.style.transform = 'translateY(16px)';
      parent.style.transition = 'opacity 0.5s ease 0.1s, transform 0.5s ease 0.1s';
      setTimeout(function() {
        parent.style.opacity = '1';
        parent.style.transform = 'translateY(0)';
      }, 150);
    }
  }

  // Subtle pulse for overdue alert
  function setupOverduePulse() {
    var alert = document.querySelector('.overdue-alert');
    if (!alert) return;
    // Already handled by CSS animation
  }

  // Click ripple effect for QA buttons
  function setupQAButtonRipples() {
    document.querySelectorAll('.qa-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        var ripple = document.createElement('span');
        var rect = btn.getBoundingClientRect();
        var size = Math.max(rect.width, rect.height);
        ripple.style.cssText = [
          'position:absolute',
          'width:' + size + 'px',
          'height:' + size + 'px',
          'left:' + (e.clientX - rect.left - size/2) + 'px',
          'top:' + (e.clientY - rect.top - size/2) + 'px',
          'background:rgba(99,102,241,0.25)',
          'border-radius:50%',
          'transform:scale(0)',
          'animation:qa-ripple 0.5s ease',
          'pointer-events:none'
        ].join(';');
        btn.style.position = 'relative';
        btn.style.overflow = 'hidden';
        btn.appendChild(ripple);
        setTimeout(function() { ripple.remove(); }, 500);
      });
    });
    if (!document.getElementById('qa-ripple-style')) {
      var s = document.createElement('style');
      s.id = 'qa-ripple-style';
      s.textContent = '@keyframes qa-ripple{to{transform:scale(2.5);opacity:0}}';
      document.head.appendChild(s);
    }
  }

  // Productivity ring color pulse when score is low
  function setupProdRingPulse() {
    var ring = document.getElementById('prod-ring');
    if (!ring) return;
    var score = parseInt(document.getElementById('prod-num')?.textContent || '0');
    if (score < 30) {
      ring.style.filter = 'drop-shadow(0 0 8px rgba(244,63,94,0.6))';
    } else if (score >= 75) {
      ring.style.filter = 'drop-shadow(0 0 8px rgba(16,185,129,0.5))';
    }
  }

  // Init all on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      setTimeout(animateActivityFeed, 300);
      setTimeout(animateQuickStats, 400);
      setTimeout(revealActivitySection, 200);
      setTimeout(setupQAButtonRipples, 100);
      setTimeout(setupProdRingPulse, 1500);
    });
  } else {
    setTimeout(animateActivityFeed, 300);
    setTimeout(animateQuickStats, 400);
    setTimeout(revealActivitySection, 200);
    setTimeout(setupQAButtonRipples, 100);
    setTimeout(setupProdRingPulse, 1500);
  }
})();
