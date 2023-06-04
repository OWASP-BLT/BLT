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


