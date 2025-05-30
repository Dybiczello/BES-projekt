const ctx = document.getElementById('chart').getContext('2d');

const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [{
      label: 'Temperatura (°C)',
      data: [],
      borderColor: 'rgba(255, 99, 132, 1)',
      backgroundColor: 'rgba(255, 99, 132, 0.2)',
      tension: 0.3,
      pointRadius: 4,
      pointBackgroundColor: 'rgba(255,99,132,1)'
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: {
        position: 'bottom'
      }
    },
    scales: {
      x: {
        type: 'time',
        time: {
          unit: 'minute'
        },
        title: {
          display: true,
          text: 'Czas'
        }
      },
      y: {
        title: {
          display: true,
          text: 'Temperatura (°C)'
        }
      }
    }
  }
});

const ws = new WebSocket("wss://" + location.host + "/ws");

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  const now = new Date();

  const temperature = data.temperature;
  document.getElementById("current-temp").textContent = `${temperature.toFixed(2)} °C`;

  chart.data.labels.push(now);
  chart.data.datasets[0].data.push(temperature);
  chart.update();
};
