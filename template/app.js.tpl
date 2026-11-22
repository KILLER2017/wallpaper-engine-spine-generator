(function () {
  'use strict';
  var canvas = document.getElementById('stage');
  var loading = document.getElementById('loading');
  var ui = { zoom: {{ZOOM}}, x: {{X}}, y: {{Y}}, speed: {{SPEED}}, fpsLimit: {{FPSLIMIT}}, alignH: '{{ALIGNH}}', alignV: '{{ALIGNV}}', expression: 'normal' };
  var gl, renderer, skeleton, state;
  var hostPaused = false, occluded = false;
  var rafId = 0, lastFrame = null, lastFrameAt = 0;
  var globalFps = 0, lastRenderAt = 0;

  var ATLAS = '{{ATLAS}}';
  var SKEL  = '{{SKEL}}';
  var PNG   = '{{PNG}}';
  var ANIM  = '{{ANIM}}';

  async function load(file) {
    var response = await fetch('assets/' + file);
    if (!response.ok) throw new Error('无法加载 ' + file);
    return response;
  }

  function loadImage(file) {
    return new Promise(function (resolve, reject) {
      var img = new Image();
      img.onload = function () { resolve(img); };
      img.onerror = function () { reject(new Error('无法加载 ' + file)); };
      img.src = 'assets/' + file;
    });
  }

  function viewSize() {
    return { w: window.innerWidth || document.documentElement.clientWidth || canvas.clientWidth || 1,
             h: window.innerHeight || document.documentElement.clientHeight || canvas.clientHeight || 1 };
  }

  function resize() {
    if (!renderer) return;
    var size = viewSize(), w = size.w, h = size.h;
    var limits = gl.getParameter(gl.MAX_VIEWPORT_DIMS);
    var renderBuffer = gl.getParameter(gl.MAX_RENDERBUFFER_SIZE);
    var density = Math.min(3, limits[0] / w, limits[1] / h, renderBuffer / w, renderBuffer / h);
    canvas.width = Math.max(1, Math.floor(w * density));
    canvas.height = Math.max(1, Math.floor(h * density));
    gl.viewport(0, 0, canvas.width, canvas.height);
    fit();
  }

  function fit() {
    if (!renderer || !skeleton) return;
    var size = viewSize(), w = size.w, h = size.h;
    var off = new spine.Vector2(), sz = new spine.Vector2();
    skeleton.getBounds(off, sz);
    var bw = Math.max(sz.x, 1) * 0.96, bh = Math.max(sz.y, 1) * 0.96;
    var scale = Math.max(w / bw, h / bh) * 1.04 * (ui.zoom / 100);
    var camera = renderer.camera;
    camera.viewportWidth = w / scale;
    camera.viewportHeight = h / scale;
    var cx = off.x + bw / 2;
    var cy = off.y + bh / 2;
    camera.position.set(
      cx - (ui.x - 50) / 100 * camera.viewportWidth,
      cy + (ui.y - 50) / 100 * camera.viewportHeight,
      0
    );
    camera.update();
  }

  function stopLoop() {
    if (rafId) { try { cancelAnimationFrame(rafId); } catch (e) { } rafId = 0; }
    lastFrame = null;
  }

  function applyHostPaused(paused) {
    hostPaused = !!paused;
    window.__HOSTPAUSED__ = hostPaused;
    if (hostPaused) { stopLoop(); }
    else { lastFrameAt = performance.now(); startLoop(); }
  }

  function watchOcclusion() {
    if (!skeleton || hostPaused) return;
    var gap = performance.now() - lastFrameAt;
    if (!occluded && lastFrameAt > 0 && gap > 600) { occluded = true; }
    else if (occluded && gap < 250) { occluded = false; }
  }

  function frame(now) {
    rafId = 0;
    if (hostPaused) { lastFrame = null; return; }
    var activeFps = ui.fpsLimit > 0 ? ui.fpsLimit : globalFps;
    var minInterval = activeFps > 0 ? 1000 / activeFps : 0;
    if (minInterval > 0 && lastRenderAt > 0 && now - lastRenderAt < minInterval - 1) {
      rafId = requestAnimationFrame(frame);
      return;
    }
    lastRenderAt = now;
    var dt = lastFrame === null ? 0 : Math.min(0.1, (now - lastFrame) / 1000);
    lastFrame = now;
    lastFrameAt = performance.now();
    state.update(dt * ui.speed);
    state.apply(skeleton);
    skeleton.updateWorldTransform();
    gl.clear(gl.COLOR_BUFFER_BIT);
    renderer.begin();
    renderer.drawSkeleton(skeleton, true);
    renderer.end();
    rafId = requestAnimationFrame(frame);
  }

  function startLoop() {
    if (rafId || hostPaused) return;
    lastFrame = null;
    rafId = requestAnimationFrame(frame);
  }

  function applyExpression() {
    if (!state) return;
    if (!ui.expression || ui.expression === 'normal') {
      state.clearTrack(1);
    } else {
      var entry = state.setAnimation(1, ui.expression, false);
      entry.mixDuration = 0.2;
    }
  }

  function slider(properties, key, min, max) {
    if (!properties[key]) return;
    var value = Number(properties[key].value);
    if (Number.isFinite(value)) ui[key] = Math.max(min, Math.min(max, value));
  }

  function comboValue(properties, key) {
    if (!properties[key]) return null;
    return properties[key].value;
  }

  var ALIGN_X = { left: 0, center: 50, right: 100 };
  var ALIGN_Y = { top: 0, center: 50, bottom: 100 };

  window.wallpaperPropertyListener = {
    setPaused: function (paused) { applyHostPaused(paused); },
    applyGeneralProperties: function (properties) {
      if (properties.fps) { globalFps = Number(properties.fps.value) || 0; }
    },
    applyUserProperties: function (properties) {
      slider(properties, 'zoom', 50, 200);
      slider(properties, 'x', 0, 100);
      slider(properties, 'y', 0, 100);
      slider(properties, 'speed', 0.2, 2);
      if (properties.fpsLimit) { ui.fpsLimit = Number(properties.fpsLimit.value) || 0; }
      var ex = comboValue(properties, 'expression');
      if (ex !== null) { ui.expression = ex; applyExpression(); }
      var ah = comboValue(properties, 'alignH');
      if (ah !== null && ALIGN_X[ah] !== undefined) { ui.alignH = ah; ui.x = ALIGN_X[ah]; }
      var av = comboValue(properties, 'alignV');
      if (av !== null && ALIGN_Y[av] !== undefined) { ui.alignV = av; ui.y = ALIGN_Y[av]; }
      fit();
    }
  };

  async function init() {
    gl = canvas.getContext('webgl', { alpha: true, antialias: false, premultipliedAlpha: true });
    if (!gl) throw new Error('无法创建 WebGL 场景');
    renderer = new spine.webgl.SceneRenderer(canvas, gl);
    gl.clearColor(0, 0, 0, 0);

    var results = await Promise.all([
      load(ATLAS).then(function (r) { return r.text(); }),
      load(SKEL).then(function (r) { return r.arrayBuffer(); }),
      loadImage(PNG)
    ]);
    var pages = {};
    pages[PNG] = results[2];
    var atlas = new spine.TextureAtlas(results[0].trimStart().replace(/^pma:.*\r?\n/gm, ''), function (name) {
      if (!pages[name]) throw new Error('图集缺少 ' + name);
      return new spine.webgl.GLTexture(gl, pages[name]);
    });
    var data = new spine.SkeletonBinary(new spine.AtlasAttachmentLoader(atlas))
      .readSkeletonData(new Uint8Array(results[1]));
    skeleton = new spine.Skeleton(data);
    skeleton.setToSetupPose();
    skeleton.updateWorldTransform();
    var settings = new spine.AnimationStateData(data);
    settings.defaultMix = 0.2;
    state = new spine.AnimationState(settings);
    state.setAnimation(0, ANIM, true);

    resize();
    window.addEventListener('resize', resize);

    lastFrameAt = performance.now();
    setInterval(watchOcclusion, 150);
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) { occluded = true; }
      else { lastFrameAt = performance.now(); occluded = false; }
    });

    startLoop();
    loading.hidden = true;
    window.__READY__ = true;
  }

  init().catch(function (error) {
    window.__ERR__ = String(error && error.stack || error);
    loading.textContent = error.message || '壁纸加载失败';
    console.error(error);
  });
})();
