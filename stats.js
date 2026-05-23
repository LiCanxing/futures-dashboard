(function(){
  var S='https://futures-stats.onrender.com';
  var uid=localStorage.getItem('fuid')||(function(){var u='u'+Math.random().toString(36).slice(2,10);localStorage.setItem('fuid',u);return u;})();
  fetch(S+'/track',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uid:uid,type:'pageview',url:location.href})}).catch(function(){});
  document.addEventListener('click',function(e){
    var t=e.target.closest('[data-code]');
    if(t&&t.dataset.code){
      fetch(S+'/track',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uid:uid,type:'click',code:t.dataset.code})}).catch(function(){});
    }
  });
})();
