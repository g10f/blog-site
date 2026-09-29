// jump link to the registration form: hide it when there is no form on the page
// or while the form is already visible
(function () {
  const link = document.getElementById('registration-form-link');
  if (!link) return;
  const form = document.getElementById('registration-form');
  if (!form) {
    link.classList.add('d-none');
    return;
  }
  if (!('IntersectionObserver' in window)) return;
  new IntersectionObserver(function (entries) {
    link.classList.toggle('d-none', entries[0].isIntersecting);
  }).observe(form);
})();
