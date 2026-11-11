/* Display settings, applied before the page is drawn. Shared with sumanrath.org through one cookie. */
(function () {
  var d = document.documentElement, v = "", m = document.cookie.match(/(?:^|; )disp=([^;]*)/);
  if (m) v = decodeURIComponent(m[1]);
  var o = {};
  v.split(",").forEach(function (p) { var k = p.split(":"); if (k[0] && k[1]) o[k[0]] = k[1]; });
  if (/^[1-3]$/.test(o.ts || "")) d.setAttribute("data-ts", o.ts);
  if (o.sp === "1") d.setAttribute("data-sp", "1");
  if (o.ul === "1") d.setAttribute("data-ul", "1");
  if (o.rm === "1") d.setAttribute("data-rm", "1");
  var ct = /^(light|dark|hcl|hcd)$/.test(o.ct || "") ? o.ct : "auto";
  if (ct !== "auto") d.setAttribute("data-ct", ct);
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  function scheme() {
    var c = d.getAttribute("data-ct") || "auto";
    d.classList.toggle("dk", c === "dark" || c === "hcd" || (c === "auto" && !!(mq && mq.matches)));
    d.classList.toggle("lt", c === "light" || c === "hcl");
  }
  scheme();
  if (mq && mq.addEventListener) mq.addEventListener("change", scheme);
  window.atlasDisplayScheme = scheme;
})();
