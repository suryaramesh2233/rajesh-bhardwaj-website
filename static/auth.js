document.querySelectorAll('[data-auth]').forEach(shell => {
  const card = shell.querySelector('.auth-card');
  shell.addEventListener('pointermove', e => {
    const r = shell.getBoundingClientRect();
    const x = ((e.clientX-r.left)/r.width-.5)*2;
    const y = ((e.clientY-r.top)/r.height-.5)*2;
    card.style.setProperty('--mx', `${x*10}px`);
    card.style.setProperty('--my', `${y*10}px`);
    card.style.setProperty('--rx', `${y*-1.5}deg`);
    card.style.setProperty('--ry', `${x*1.8}deg`);
  });
  shell.addEventListener('pointerleave', () => {
    card.style.setProperty('--mx','0px'); card.style.setProperty('--my','0px'); card.style.setProperty('--rx','0deg'); card.style.setProperty('--ry','0deg');
  });
});
