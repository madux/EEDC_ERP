odoo.define('inventory.form.ui', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    // ----- Dummy datasets (UI-only) -----
    const DUMMY = {
        operationTypes: ['Delivery', 'Internal transfer', 'Receipt'],
        statusOptions: ['Draft', 'Allocated', 'Completed', 'Canceled'],
        customers: [
            { id: 1, name: 'Acme Ltd.' },
            { id: 2, name: 'Globex Corp.' },
            { id: 3, name: 'Initech' },
        ],
        locations: [
            { id: 11, name: 'Enugu' },
            { id: 12, name: 'Abuja' },
            { id: 13, name: 'Lagos' },
        ],
        products: [
            { id: 101, name: 'Camry', uom: 'm', colors: ['Red', 'Blue', 'Black'] },
            { id: 102, name: 'TV', uom: 'kg', colors: ['Blue', 'Gray'] },
        ],
    };

    function uid() {
        return Math.random().toString(36).slice(2, 8);
    }

    publicWidget.registry.InventoryFormUI = publicWidget.Widget.extend({
        selector: '#inv-root',

        events: {
            'click #btnAddLine': '_onAddLine',
            'click #btnTruck': '_openTruck',
            'click [data-close]': '_closeModal',
            'click #btnSaveTruck': '_saveTruck',
            'click #btnFakeSubmit': '_previewJSON',
            'click #opTypeBtn': '_toggleOpMenu',
        },

        start() {
            this.$root = this.$('#inv-root');
            this.$overlay = $('#inv-overlay');
            this.$truckModal = $('#truckModal');
            this.$stocksBody = $('#stocksBody');
            this.$opBtn = $('#opTypeBtn');
            this.$opMenu = $('#opTypeMenu');

            this.state = this._loadDraft() || {
                customer: '', operationType: null, reference: '',
                truck: { regNo: '', driver: '', driverNo: '', address: '', startLoc: '', destLoc: '' },
                lines: []
            };

            this._bindTopInputs();
            this._renderOpMenu();
            this._renderLines();

            $(document).on('click.inv', (e) => this._docClick(e));
            $(document).on('keydown.inv', (e) => this._docKey(e));

            return this._super.apply(this, arguments);
        },

        _bindTopInputs() {
            const self = this;
            this.$('.inv-field').each(function () {
                const key = this.dataset.key;
                if (!key) return;
                this.value = self.state[key] || '';
                $(this).on('input change', (ev) => {
                    self.state[key] = ev.target.value;
                    self._saveDraft();
                });
            });
            const val = this.state.operationType || 'Select operation type ▽';
            this.$('.inv-select__value').text(val);
        },

        _renderOpMenu() {
            const html = DUMMY.operationTypes.map((txt, i) => (
                `<div class="inv-menu__item" role="option" data-value="${_.escape(txt)}">${_.escape(txt)}</div>` +
                (i < DUMMY.operationTypes.length - 1 ? '<div class="inv-menu__sep"></div>' : '')
            )).join('');
            this.$opMenu.html(html);
            this.$opMenu.on('click', '.inv-menu__item', (ev) => {
                const value = $(ev.currentTarget).data('value');
                this.state.operationType = value;
                this.$('.inv-select__value').text(value);
                this._saveDraft();
                this._hideOpMenu();
            });
        },

        _toggleOpMenu(ev) {
            ev.preventDefault();
            const btn = this.$opBtn[0];
            const rect = btn.getBoundingClientRect();
            this.$opMenu.css({ top: rect.bottom + window.scrollY + 6, left: rect.left + window.scrollX, minWidth: rect.width });
            this.$opMenu.attr('hidden', !this.$opMenu.attr('hidden'));
        },
        _hideOpMenu() { this.$opMenu.attr('hidden', true); },

        _renderLines() {
            const lines = this.state.lines;
            if (!lines.length) {
                this.$stocksBody.html('<tr class="inv-empty"><td colspan="9"><span class="text-muted">No stock lines yet. Click “Add Stocks”.</span></td></tr>');
                return;
            }
            const rows = lines.map(l => this._lineRowHTML(l)).join('');
            this.$stocksBody.html(rows);
            this.$stocksBody.find('input,select').off('input change');
            this.$stocksBody.find('input[data-k], select[data-k]').on('change input', (e) => this._onCellChange(e));
            this.$stocksBody.find('[data-action="del"]').on('click', (e) => this._delLine($(e.currentTarget).data('id')));
        },

        _lineRowHTML(l) {
            const prodOpts = DUMMY.products.map(p => `<option value="${p.id}" ${p.id === l.product ? 'selected' : ''}>${_.escape(p.name)}</option>`).join('');
            const locOpts = DUMMY.locations.map(p => `<option value="${p.id}" ${p.id === l.src ? 'selected' : ''}>${_.escape(p.name)}</option>`).join('');
            const locOpts2 = DUMMY.locations.map(p => `<option value="${p.id}" ${p.id === l.dest ? 'selected' : ''}>${_.escape(p.name)}</option>`).join('');
            const colorOpts = (this._productById(l.product)?.colors || ['—']).map(c => `<option value="${_.escape(c)}" ${c === l.colour ? 'selected' : ''}>${_.escape(c)}</option>`).join('');
            const statOpts = DUMMY.statusOptions.map(s => `<option value="${s}" ${s === l.status ? 'selected' : ''}>${s}</option>`).join('');
            return `
        <tr>
          <td><select class="form-select" data-k="product" data-id="${l.id}">${prodOpts}</select></td>
          <td><input class="form-control" type="number" data-k="qty" data-id="${l.id}" value="${l.qty}"></td>
          <td><select class="form-select" data-k="src" data-id="${l.id}">${locOpts}</select></td>
          <td><select class="form-select" data-k="dest" data-id="${l.id}">${locOpts2}</select></td>
          <td><input class="form-control" type="number" data-k="reserve" data-id="${l.id}" value="${l.reserve}"></td>
          <td><input class="form-control" type="text" data-k="uom" data-id="${l.id}" value="${l.uom}"></td>
          <td><select class="form-select" data-k="colour" data-id="${l.id}">${colorOpts}</select></td>
          <td><select class="form-select" data-k="status" data-id="${l.id}">${statOpts}</select></td>
          <td class="text-center"><button class="btn btn-sm btn-light" data-action="del" data-id="${l.id}"><i class="fa fa-trash-o"></i></button></td>
        </tr>`;
        },

        _productById(id) { return DUMMY.products.find(p => p.id === Number(id)); },

        _onAddLine() {
            if (this.$stocksBody.find('.inv-empty').length) this.$stocksBody.empty();
            const first = DUMMY.products[0];
            const line = {
                id: uid(), product: first.id, qty: 1, src: DUMMY.locations[0].id, dest: DUMMY.locations[1].id,
                reserve: 0, uom: first.uom, colour: (first.colors[0] || ''), status: 'Draft'
            };
            this.state.lines.push(line);
            this._saveDraft();
            this._renderLines();
        },

        _delLine(id) {
            this.state.lines = this.state.lines.filter(l => l.id !== id);
            this._saveDraft();
            this._renderLines();
        },

        _onCellChange(e) {
            const id = $(e.target).data('id');
            const key = e.target.dataset.k;
            const v = e.target.value;
            const line = this.state.lines.find(l => l.id === id);
            line[key] = v;
            this._saveDraft();
        },

        _openTruck() {
            this.$overlay.addClass('is-open');
            this.$truckModal.removeAttr('hidden');
            $('#inv-root').addClass('blurred');
        },
        _closeModal() {
            this.$overlay.removeClass('is-open');
            this.$truckModal.attr('hidden', 'hidden');
            $('#inv-root').removeClass('blurred');
        },
        _saveTruck() {
            const self = this;
            this.$truckModal.find('.inv-truck').each(function () { self.state.truck[this.dataset.key] = this.value || ''; });
            this._saveDraft();
            this._closeModal();
        },

        _docClick(e) {
            const $t = $(e.target);
            if (!$t.closest('#opTypeBtn').length && !$t.closest('#opTypeMenu').length) this._hideOpMenu();
            if ($t.is('#inv-overlay')) this._closeModal();
        },
        _docKey(e) {
            if (e.key === 'Escape') { this._hideOpMenu(); this._closeModal(); }
        },

        _saveDraft() {
            try { localStorage.setItem('inv_form_draft', JSON.stringify(this.state)); } catch (_) { }
        },
        _loadDraft() {
            try { return JSON.parse(localStorage.getItem('inv_form_draft') || 'null'); } catch (_) { return null; }
        },

        _previewJSON() {
            const invalids = [];
            if (!this.state.customer?.trim()) invalids.push('Customer');
            if (!this.state.operationType) invalids.push('Operation type');
            if (!this.state.lines.length) invalids.push('At least one stock line');
            this.$('.inv-field[data-key="customer"]').toggleClass('is-invalid', !this.state.customer?.trim());
            this.$('#opTypeBtn').toggleClass('is-invalid', !this.state.operationType);
            if (invalids.length) return alert('Please fix: ' + invalids.join(', '));
            alert(JSON.stringify(this.state, null, 2));
        },
    });

    return publicWidget.registry.InventoryFormUI;
});