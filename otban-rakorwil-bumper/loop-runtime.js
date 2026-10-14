// Shared loop runtime: render(t) is pure in t and periodic with LOOP seconds.
// Preview: open the HTML (plays forever). Recorder: window.__seek(t).
(function(){
  const fit=()=>{const k=Math.min(innerWidth/1920,innerHeight/1080);document.getElementById('stage').style.transform=`scale(${k})`};
  addEventListener('resize',fit);fit();
  window.__duration=LOOP;
  window.__seek=t=>window.render(((t%LOOP)+LOOP)%LOOP);
  const still=new URLSearchParams(location.search).has('still');let t0=performance.now();
  function tick(now){if(window.__recording||still)return;window.render(((now-t0)/1000)%LOOP);requestAnimationFrame(tick)}
  document.fonts.ready.then(()=>{window.render(0);window.__ready=true;requestAnimationFrame(tick)});
})();
