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
  console.log("Received:", event.data);
  const msg = JSON.parse(event.data);

  if (msg.type === "history") {
    const history = msg.data;

    history.forEach(data => {
      const timestamp = new Date(data.timestamp);
      const temperature = data.temperature;

      chart.data.labels.push(timestamp);
      chart.data.datasets[0].data.push(temperature);
    });

    chart.update();
  }

  // Obsługa nowych danych (na żywo)
  if (!msg.type) {
    const temperature = msg.temperature;
    const timestamp = new Date(msg.timestamp);

    document.getElementById("current-temp").textContent = `${temperature.toFixed(2)} °C`;

    chart.data.labels.push(timestamp);
    chart.data.datasets[0].data.push(temperature);
    chart.update();
  }
};
