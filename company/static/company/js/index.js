const navItems = document.querySelectorAll('.side-nav__item');
const removeClasses = () => {
  navItems.forEach(eachItem => {
    eachItem.classList.remove('side-nav__item-active');
  });
}

navItems.forEach(eachItem => {
  eachItem.addEventListener('click', function() {
      removeClasses();
    eachItem.classList.add('side-nav__item-active');
  });
});

const ctx = document.getElementById('myChart');

new Chart(ctx, {
  type: 'bar',
  data: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Des'],
    datasets: [{
      label: 'Expense',
      data: [11, 3, 14, 7, 4, 15, 7, 9, 15, 13, 7, 14],
      borderWidth: 1,
      borderRadius: 30,
      barThickness: 12,
      backgroundColor: [
        'rgba(114, 92, 255, 1)'
      ],
      borderColor: [
        'rgba(114, 92, 255, 1)'
      ],
      hoverBackgroundColor: [
        'rgba(28, 30, 35, 1)'
      ],
      hoverBorderColor: [
        'rgba(28, 30, 35, 1)'
      ],
    }]
  },
  options: {
    responsive: true,
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
            // Include a dollar sign in the ticks
            callback: function(value, index, ticks) {
                return '$' + value + 'k';
            },
            stepSize: 5,
        },
      },
      x: {
        grid: {
            display: false
        }
      }
    },
    plugins: {
        legend: {
          display:false,
          labels: {
            font: {
                size: 12,
                family: "'Plus Jakarta Sans', sans-serif",
                lineHeight: 18,
                weight: 600
            }
          }
        }
    }
  }
});

const ctx2 = document.getElementById('myChart2');

new Chart(ctx2, {
  type: 'doughnut',
  data: {
    datasets: [{
      label: 'Overall Spending',
      data: [8000, 2130, 1510, 2245, 4385, 1000,400,100],
      borderRadius: 5,
      cutout: 80,
      backgroundColor: [
        'rgb(235, 124, 166)',
        'rgb(255, 172, 200)',
        'rgb(204, 111, 248)',
        'rgb(124, 92, 252)',
        'rgb(92, 175, 252)',
        'rgb(161, 169, 254)',
        'rgb(161, 169, 254)',
        'rgb(161, 169, 254)'
      ],
      hoverOffset: 4,
      spacing: 8
    }]
  },
  options: {
    plugins: {
      legend: {
        display: false
      }
    }
  }
});


var bugTypePie = document.getElementById('bugTypePie').getContext('2d');

  // Create the pie chart
  new Chart(bugTypePie, {
    type: 'pie',
    data: {
      labels: ['GENERAL', 'NUMBER ERR', 'FUNCTIONAL', "PERFORMANCE", "SECURITY", "TYPO", "DESIGN", "SERVER DOWN"],
      datasets: [{
        label: 'Pie Chart',
        data: [50, 30, 20, 14,54,33,1],
        backgroundColor: [
          'rgb(255, 99, 132)',
          'rgb(54, 162, 235)',
          'rgb(255, 205, 86)'
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });

  var domainPie = document.getElementById('domainPie').getContext('2d');

  // Create the pie chart
  new Chart(domainPie, {
    type: 'pie',
    data: {
      labels: ['google.com', 'gmail.com', 'bugheist.com'],
      datasets: [{
        label: 'Pie Chart',
        data: [50, 30, 20],
        backgroundColor: [
          'rgb(255, 99, 132)',
          'rgb(54, 162, 235)',
          'rgb(255, 205, 86)'
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });