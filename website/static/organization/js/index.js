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


