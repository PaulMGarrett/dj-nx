const wakeLockDiv = document.querySelector('#wakeLockDiv');

let wakeLock = null;

if ('WakeLock' in window && 'request' in window.WakeLock) {
  console.log('Wake Lock case A');

  const requestWakeLock = () => {
    const controller = new AbortController();
    const signal = controller.signal;
    window.WakeLock.request('screen', {signal})
    .catch((e) => {
      if (e.name === 'AbortError') {
        console.log('Wake Lock was aborted A');
        wakeLockDiv.textContent = 'Wake Lock was aborted A';
      } else {
        console.error(`${e.name}, ${e.message} A`);
        wakeLockDiv.textContent = `${e.name}, ${e.message} A`;
      }
    });
    console.log('Wake Lock is active A');
    wakeLockDiv.textContent = 'Wake Lock is active';
    return controller;
  };

  const handleVisibilityChange = () => {
    if (wakeLock !== null && document.visibilityState === 'visible') {
      wakeLock = requestWakeLock();
    }
  };

} else if ('wakeLock' in navigator && 'request' in navigator.wakeLock) {
  console.log('Wake Lock case B');
  
  const requestWakeLock = async () => {
    try {
      wakeLock = await navigator.wakeLock.request('screen');
      wakeLock.addEventListener('release', (e) => {
        console.log(e);
        console.log('Wake Lock was released B');
        wakeLockDiv.textContent = 'Wake Lock was released B';
      });
      console.log('Wake Lock is active B');
      wakeLockDiv.textContent = 'Wake Lock is active B';
    } catch (e) {
      console.error(`${e.name}, ${e.message} B`);
      wakeLockDiv.textContent = `${e.name}, ${e.message} B`;
    } 
  };
  
  const handleVisibilityChange = async () => {
    if (wakeLock !== null && document.visibilityState === 'visible') {
      await requestWakeLock();
    }
  };
  
} else {
  console.error('Wake Lock API not supported.');
  wakeLockDiv.textContent = 'Wake Lock API not supported.';
}

document.addEventListener('visibilitychange', handleVisibilityChange);
