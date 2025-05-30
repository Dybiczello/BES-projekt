// Pobieramy kontekst canvas z HTML
const ctx = document.getElementById('chart').getContext('2d');

// Tworzymy wykres liniowy Chart.js
const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [], // tutaj będą timestampy
    datasets: [{
      label: 'Temperatura [°C]',
      data: [], // tutaj będą wartości temperatury
      borderColor: 'rgba(75, 192, 192, 1)',
      borderWidth: 2,
      fill: false,
      tension: 0.1,
    }]
  },
  options: {
    scales: {
      x: {
        type: 'time',           // oś czasu
        time: {
          unit: 'minute',
          displayFormats: {
            minute: 'HH:mm:ss'
          }
        },
        title: {
          display: true,
          text: 'Czas'
        }
      },
      y: {
        title: {
          display: true,
          text: 'Temperatura [°C]'
        },
        suggestedMin: 0,
        suggestedMax: 40
      }
    }
  }
});

// Tworzymy połączenie WebSocket
const protocol = location.protocol === 'https:' ? 'wss://' : 'ws://';
const ws = new WebSocket(protocol + location.host + "/ws");

// Obsługa otrzymania wiadomości przez WebSocket
ws.onmessage = function(event) {
  console.log("Otrzymano wiadomość WebSocket:", event.data);
  const data = JSON.parse(event.data);

  const temperature = data.temperature;
  const timestamp = new Date(data.timestamp);

  // Aktualizujemy widoczny na stronie aktualny odczyt temperatury
  document.getElementById("current-temp").textContent = `${temperature.toFixed(2)} °C`;

  // Dodajemy dane do wykresu
  chart.data.labels.push(timestamp);
  chart.data.datasets[0].data.push(temperature);

  // Limitujemy rozmiar danych na wykresie, np. 30 ostatnich punktów
  if(chart.data.labels.length > 30) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }

  chart.update();
};

// Obsługa błędów WebSocket
ws.onerror = function(event) {
  console.error("WebSocket error:", event);
};

// Opcjonalnie: informacja o otwarciu połączenia
ws.onopen = function() {
  console.log("WebSocket połączony");
};
