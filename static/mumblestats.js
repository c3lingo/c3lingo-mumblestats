document.addEventListener("DOMContentLoaded", function(event) {
  let elem = document.querySelector('#xhrstats')
  let first = true;

  let statsDisplayMeterWidthForDb = function(value) {
    // scale: +3dBFS == 82 units width of bar, 3dB = 2
    return 88 + (value - 3) * 2;
  }

  let createStatsDisplayGradation = function(value) {
    let html = '';
    let pos = statsDisplayMeterWidthForDb(value) + 6;
    let label = '' + value.toFixed(0) + (value < 0 ? '&nbsp;' : '');
    html += '<text x="' + pos + '" y="3.5" fill="#ccc" font-family="Arial, Helvetica, sans-serif" font-size="3" text-anchor="middle">' + label + '</text>';
    html += '<line x1="' + pos + '" y1="4" x2="' + pos + '" y2="5" stroke="#ccc" stroke-width=".2"/>'
    return html;
  }

  let createStatsDisplay = function(channel) {
    var channelStats = document.createElement('div');
    var classAttr = document.createAttribute('class');
    classAttr.value = 'channelStats';
    channelStats.setAttributeNode(classAttr);

    let html = ''

    html += '<div class="channelStatsLabel">';
    html += '<h2 class="channelStatsName">' + channel + '</h2>';
    html += '<div class="channelStatsUsers">';
    html += '<span id="channelStatsUsers-' + channel + '">0</span> users';
    html += '</div>';
    html += '</div>';
    html += '<div class="channelStatsMeter">'
    html += '<svg viewbox="0 0 100 10">';
    html += '<defs>';
    html += '<linearGradient id="anodized_metal" x1="0" y1="0" x2="100" y2="30" gradientUnits="userSpaceOnUse">';
    html += '<stop offset="3%" style="stop-color:#111;stop-opacity:100%"/>';
    html += '<stop offset="10%" style="stop-color:#333;stop-opacity:100%"/>';
    html += '<stop offset="15%" style="stop-color:#222;stop-opacity:100%"/>';
    html += '<stop offset="25%" style="stop-color:#333;stop-opacity:100%"/>';
    html += '<stop offset="33%" style="stop-color:#111;stop-opacity:100%"/>';
    html += '<stop offset="38%" style="stop-color:#222;stop-opacity:100%"/>';
    html += '<stop offset="42%" style="stop-color:#111;stop-opacity:100%"/>';
    html += '<stop offset="57%" style="stop-color:#333;stop-opacity:100%"/>';
    html += '<stop offset="63%" style="stop-color:#222;stop-opacity:100%"/>';
    html += '<stop offset="75%" style="stop-color:#333;stop-opacity:100%"/>';
    html += '<stop offset="88%" style="stop-color:#111;stop-opacity:100%"/>';
    html += '<stop offset="92%" style="stop-color:#333;stop-opacity:100%"/>';
    html += '</linearGradient>';
    html += '<linearGradient id="meter_display" x1="0" y1="0" x2="100" y2="0" gradientUnits="userSpaceOnUse">';
    html += '<stop offset="0%" style="stop-color:#00f;stop-opacity:100%"/>';
    html += '<stop offset="40%" style="stop-color:#0f0;stop-opacity:100%"/>';
    html += '<stop offset="75%" style="stop-color:#0f0;stop-opacity:100%"/>';
    html += '<stop offset="82%" style="stop-color:#f00;stop-opacity:100%"/>';
    html += '<stop offset="100%" style="stop-color:#f00;stop-opacity:100%"/>';
    html += '</linearGradient>';
    html += '</defs>';

    html += '<rect x="0" y="0" width="100" height="10" fill="url(#anodized_metal)"/>';
    html += '<path d="M 6 9 L 6 6 L 94 6" fill="none" stroke="#000" stroke-width=".2"/>';
    html += '<path d="M 6 9 L 94 9 L 94 6" fill="none" stroke="#444" stroke-width=".2"/>';
    for (let i = 3; i >= -3; i -= 3) {
      html += createStatsDisplayGradation(i);
    }
    for (let i = -6; i >= -36; i -= 6) {
      html += createStatsDisplayGradation(i);
    }
    html += '<text x="1" y="3.5" font-family="Arial, Helvetica, sans-serif" fill="#ccc" font-size="3" text-anchor="left">dBFS</text>';
    html += '<rect id="channelStatsMeter-' + channel + '" x="6" y="6" width="88" height="3" fill="url(#meter_display)"/>';
    html += '<rect id="channelStatsPeak-' + channel + '" x="93.5" y="5.5" width="1" height="4" fill="#f00" stroke="#000" stroke-width=".2"/>';

    html += '</svg></div>';


    channelStats.innerHTML = html;

    elem.appendChild(channelStats);
  }

  let updateStats = function() {
    let xhr = new XMLHttpRequest();
    xhr.open('GET', '/stats');
    xhr.send()
    xhr.onload = function() {
      if (xhr.status != 200)
        return;
      let json = JSON.parse(xhr.response)
      let r = ''
      if (first) {
        first = false;
        for (const [name, values] of Object.entries(json)) {
          createStatsDisplay(name);
        }
        return;
      }
      for (const [name, values] of Object.entries(json)) {
        let users = document.getElementById('channelStatsUsers-' + name);
        users.innerHTML = values.users;
        let rms = document.getElementById('channelStatsMeter-' + name);
        let value = statsDisplayMeterWidthForDb(values.rms);
        if (value < 2)
          value = 2;
        rms.setAttribute('width', value);
        let peak = document.getElementById('channelStatsPeak-' + name);
        value = statsDisplayMeterWidthForDb(values.peak);
        if (value < 2)
          value = -999;
        peak.setAttribute('x', value);
      }
      //elem.innerHTML = json['Test'].users;
    }
  }

  // createStatsDisplay('Test');

  setInterval(updateStats, 100);
});
