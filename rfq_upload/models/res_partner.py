from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    is_vendor = fields.Boolean(
        string="Vendor",
        compute="_compute_is_vendor",
        inverse="_inverse_is_vendor",
        store=True
    )
    vendor_code = fields.Char("Vendor Code", help="Unique code to identify this vendor in RFQ processes")
    
    @api.depends("supplier_rank")
    def _compute_is_vendor(self):
        for partner in self:
            partner.is_vendor = partner.supplier_rank > 0

    def _inverse_is_vendor(self):
        for partner in self:
            if partner.is_vendor and partner.supplier_rank == 0:
                partner.supplier_rank = 1
            elif not partner.is_vendor:
                partner.supplier_rank = 0
    
    @api.constrains('vendor_code', 'is_vendor')
    def _check_vendor_code_unique(self):
        """Ensure vendor code is unique when partner is marked as vendor"""
        for partner in self:
            if partner.is_vendor and partner.vendor_code:
                existing = self.search([
                    ('vendor_code', '=', partner.vendor_code),
                    ('is_vendor', '=', True),
                    ('id', '!=', partner.id)
                ], limit=1)
                if existing:
                    raise ValidationError(_("Vendor code '%s' already exists for vendor '%s'. Please use a unique vendor code.") % (partner.vendor_code, existing.name))
    
    @api.onchange('is_vendor')
    def _onchange_is_vendor(self):
        """Set supplier_rank when marking as vendor"""
        if self.is_vendor:
            self.supplier_rank = 1
            if not self.vendor_code:
                self._suggest_vendor_code()
        else:
            self.vendor_code = False
    
    def _suggest_vendor_code(self):
        """Suggest a vendor code based on partner name"""
        if self.name and self.is_vendor:
            words = self.name.strip().upper().split()
            if len(words) == 1:
                base_code = words[0][:3]
            elif len(words) >= 2:
                base_code = ''.join([word[0] for word in words[:4]])
            else:
                base_code = "VEN"
            
            suggested_code = base_code
            counter = 1
            while self.search([('vendor_code', '=', suggested_code), ('is_vendor', '=', True)], limit=1):
                counter += 1
                suggested_code = f"{base_code}{counter:03d}"
                if counter > 999:
                    break
            
            self.vendor_code = suggested_code
    
    @api.model
    def create(self, vals):
        """Override create to auto-generate vendor code if needed"""
        partner = super(ResPartner, self).create(vals)
        
        if partner.is_vendor and not partner.vendor_code:
            partner._suggest_vendor_code()
            
        return partner
    
    def name_get(self):
        """Override name_get to include vendor code in display name for vendors"""
        result = []
        for partner in self:
            if partner.is_vendor and partner.vendor_code:
                name = f"{partner.name} [{partner.vendor_code}]"
            else:
                name = partner.name
            result.append((partner.id, name))
        return result
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Override name_search to include vendor code in search"""
        if args is None:
            args = []
        
        if name:
            partners = self.search([('name', operator, name)] + args, limit=limit)
            
            if len(partners) < limit and operator in ('ilike', '=', 'like'):
                vendor_partners = self.search([
                    ('vendor_code', operator, name),
                    ('is_vendor', '=', True),
                    ('id', 'not in', partners.ids)
                ] + args, limit=limit - len(partners))
                partners = partners | vendor_partners
        else:
            partners = self.search(args, limit=limit)
        
        return partners.name_get()
    
    def toggle_vendor_status(self):
        """Action to toggle vendor status"""
        for partner in self:
            partner.is_vendor = not partner.is_vendor
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Vendor Status Updated'),
                'message': _('Vendor status has been updated successfully.'),
                'sticky': False,
                'type': 'success'
            }
        }