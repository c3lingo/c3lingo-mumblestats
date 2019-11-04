document.addEventListener("DOMContentLoaded", function(event) {
  let elem = document.querySelector('#xhrstats')
  let updateStats = function() {
    let xhr = new XMLHttpRequest();
    xhr.open('GET', '/stats');
    xhr.send()
    xhr.onload = function() {
      if (xhr.status != 200)
        return;
      let json = JSON.parse(xhr.response)
      let r = ''
      for (const [name, values] of Object.entries(json)) {
        r += '<p>' + name + ': ' + values.users + '</p>\n'
        r += '<p><meter value=' + values.rms + ' min=-72 low=-36 optimum=-18 high=-9 max=3></meter> ' + values.rms.toFixed(1) + '</p>'
        r += '<p><meter value=' + values.peak + ' min=-72 low=-36 optimum=-18 high=-3 max=3></meter> ' + values.peak.toFixed(1) + '</p>'
      }
      //elem.innerHTML = json['Test'].users;
      elem.innerHTML = r;
    }
  }
  setInterval(updateStats, 100);
});
