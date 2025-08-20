odoo.define('appraisal.system.ui', function (require) {
  'use strict';

  const publicWidget = require('web.public.widget');
  const appData = require('appraisals.data');

  publicWidget.registry.AppraisalSystemUI = publicWidget.Widget.extend({
    selector: '#appraisal-root',

    events: {
      'click #btn-view-goals': '_openGoals',
      'click #btn-start-appraisal': '_openWizard',
    },

    start() {
      this.$overlay = $('#appraisal-overlay');
      this.$modalGoals = $('#modal-goals');
      this.$modalWizard = $('#modal-wizard');
      this.$root = $('#appraisal-root');

      // Gate: employee details must be valid
      this.$details = $('#employee-details .form-control');
      this.$btnGoals = $('#btn-view-goals');
      this.$btnStart = $('#btn-start-appraisal');
      this.$details.on('input change blur', () => this._validateDetails());
      this._validateDetails();

      // Call the prefill function
      this._prefillFromRid();

      // Close handlers
      $('[data-close]').on('click', () => this._closeAny());
      this.$overlay.on('click', () => this._closeAny());

      // Wizard state
      this.currentStep = 1;
      this.totalSteps = 5;
      this.$slides = $('#wizardSlides .wizard-slide');
      this.$counter = $('#wizardCounter');
      this.$title = $('#wizardTitle');
      //   this.$bar = $('#wizardBar');

      // Wizard controls
      this.$btnPrev = $('#btnPrev');
      this.$btnNext = $('#btnNext');

      this.$btnPrev.on('click', () => this._goto(this.currentStep - 1));
      this.$btnNext.on('click', () => this._goto(this.currentStep + 1));

      // Keyboard navigation inside wizard
      $(document).on('keydown', (e) => {
        if (!this.$modalWizard.hasClass('is-open')) return;
        if (e.key === 'Escape') return this._closeAny();
        if (e.key === 'ArrowLeft') return this._goto(this.currentStep - 1);
        if (e.key === 'ArrowRight') return this._goto(this.currentStep + 1);
      });

      return this._super.apply(this, arguments);
    },

    /* validation */
    _validateDetails() {
      let allValid = true;
      this.$details && this.$details.each(function () {
        const el = this;
        const $el = $(el);
        $el.removeClass('is-invalid');
        const val = (el.value || '').trim();
        if (!val) { allValid = false; return; }
        if (el.type === 'email' && el.checkValidity && !el.checkValidity()) { allValid = false; $el.addClass('is-invalid'); return; }
        if ($el.is('[data-year]') && !/^\d{4}$/.test(val)) { allValid = false; $el.addClass('is-invalid'); return; }
      });
      if (this.$btnGoals && this.$btnStart) {
        this.$btnGoals.prop('disabled', !allValid).attr('aria-disabled', !allValid);
        this.$btnStart.prop('disabled', !allValid).attr('aria-disabled', !allValid);
      }
    },

    /* Openers */
    _openGoals() { this._open(this.$modalGoals); },
    _openWizard() { this._open(this.$modalWizard); },

    _open($modal) {
      // Guards (just in case)
      if ($modal.is(this.$modalWizard) && this.$btnStart.is(':disabled')) return;
      if ($modal.is(this.$modalGoals) && this.$btnGoals.is(':disabled')) return;

      this.lastTrigger = document.activeElement; // for focus restore
      this.$overlay.addClass('is-open').attr('aria-hidden', 'false');
      $modal.addClass('is-open').attr('aria-hidden', 'false');
      this.$root.addClass('blurred');

      if ($modal.is(this.$modalWizard)) {
        this._goto(1);
        this.$modalWizard.find('.appraisal-modal__close').trigger('focus');
      } else {
        $modal.find('.appraisal-modal__close').trigger('focus');
      }
    },

    _closeAny() {
      this.$overlay.removeClass('is-open').attr('aria-hidden', 'true');
      this.$modalGoals.removeClass('is-open').attr('aria-hidden', 'true');
      this.$modalWizard.removeClass('is-open').attr('aria-hidden', 'true');
      this.$root.removeClass('blurred');
      if (this.lastTrigger) this.lastTrigger.focus();
    },

    _goto(step) {
      if (step < 1 || step > this.totalSteps) return;
      this.currentStep = step;

      // update slides
      this.$slides.removeClass('is-active');
      const $active = this.$slides.filter(`[data-step="${step}"]`).addClass('is-active');
      this.$title.text($active.data('title'));

      // counter & progress
      this.$counter.text(`${step}/${this.totalSteps}`);
      //   const pct = Math.round((step/this.totalSteps)*100);
      //   this.$bar.css('width', `${pct}%`);

      // buttons
      this.$btnPrev.prop('disabled', step === 1);
      this.$btnNext.find('span').text(step === this.totalSteps ? 'Finish' : 'Continue');
    },

    /* Prefill */
    _prefillFromRid() {
      const params = new URLSearchParams(window.location.search);
      const rid = params.get('rid');
      if (!rid) return;
      const rec = appData.getById(rid);
      if (!rec) return;
      // Fill by matching label text → input value
      const map = {
        'name': rec.employee,
        'staff id': rec.staff_id,
        'department': rec.department,
        'email': rec.email,
        'role': rec.role,
        'year': rec.year,
        'supervisor': rec.supervisor,
      };
      this.$('#employee-details .col-md-6, #employee-details .col-md-12').each(function () {
        const $wrap = $(this);
        const label = ($wrap.find('label').text() || '').trim().toLowerCase();
        for (const key in map) {
          if (label.indexOf(key) === 0) {
            $wrap.find('.form-control').val(map[key]);
            break;
          }
        }
      });
      // Re-run validation so the buttons enable
      if (this._validateDetails) this._validateDetails();
    }

  });

  return publicWidget.registry.AppraisalSystemUI;
});
