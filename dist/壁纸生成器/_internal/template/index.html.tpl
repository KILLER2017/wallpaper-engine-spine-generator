<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
  html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; background: {{BG}}; }
  #stage, #loading { position: fixed; inset: 0; }
  #stage { display: block; width: 100%; height: 100%; }
  #loading { display: grid; place-items: center; color: #eee3eb; background: #14100d; font: 14px system-ui, sans-serif; }
  [hidden] { display: none !important; }
</style>
</head>
<body>
<canvas id="stage"></canvas>
<div id="loading" role="status">正在加载壁纸…</div>
<script src="js/spine-webgl-3.8.js"></script>
<script src="js/app.js?v=1"></script>
</body>
</html>
