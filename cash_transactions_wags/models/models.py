from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError


class CashTransactionsWags(models.Model):
    _name = "cash.transactions.wags"
    _description = "Cash Transaction"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(string='Reference', copy=False)
    type = fields.Selection([
        ('open', 'Open'),
        ('close', 'Close'),
        ('in', 'In'),
        ('out', 'Out'),
    ], default="open", required=True, string="Type", tracking=True)
    category_id = fields.Many2one('cash.type.wags', string="Category", tracking=True)
    pos_session_id = fields.Many2one('pos.session.wags', string="POS Session", tracking=True)
    pos_session_close_id = fields.Many2one('pos.session.wags', string="POS Session Closing", tracking=True)
    cash_closing_id = fields.Many2one('cash.closing.wags', string="Closing Cash Reference", tracking=True)
    narration = fields.Char(string="Narration", tracking=True)
    amount = fields.Float(string="Amount", tracking=True)
    date = fields.Date(tracking=True)
    datetime = fields.Datetime(tracking=True)
    cash_id = fields.Char(tracking=True, string="Cash Id")
    create_uid = fields.Many2one('res.users', string='Created by', index=True, readonly=True, default=lambda self: self.env.user)
    cashbox_id = fields.Many2one('cash.box', string='Cash Box')
    branch_id = fields.Many2one('branch.wags', string='Branch')
    alert = fields.Boolean(string="Alert")
    attachment = fields.Binary(string="Attachment")
    attachment_name = fields.Char(string="Attachment Name")
    account_id = fields.Many2one('account.account.wags',string="Account")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)


    def name_get(self):
        result = []
        for record in self:
            if record.reference:
                name = "%s - %s - %s" % (record.reference, record.type, record.datetime)
            else:
                name = "%s - %s" % (record.type, record.datetime)
            result.append((record.id, name))
        return result

    def select_transactions(self):
        records = self.browse(self.env.context.get('active_ids'))
        session_id = self.env['pos.session.wags'].browse(self.env.context.get('session_id'))
        for rec in records:
            rec.pos_session_id = session_id.id
        session_id.update_cash_amount()


    def select_open_close_transactions(self):
        records = self.browse(self.env.context.get('active_ids'))
        session_id = self.env['pos.session.wags'].browse(self.env.context.get('session_id'))
        for rec in records:
            rec.pos_session_close_id = session_id.id
        session_id.update_open_close_amount()



    @api.model
    def create_cash_transaction(self, cash_data_list):
        messages = []

        for cash_data in cash_data_list:
            cash_id = cash_data.get('cash_id')
            existing_order = self.search([('cash_id', '=', cash_id)])

            if existing_order:
                messages.append({'status': 200, 'message': f'Cash Transaction with cash_id {cash_id} already exists.'})
            else:
                cash_transaction = self.sudo().create(cash_data)
                messages.append({'status': 200, 'message': f'Cash Transaction created successfully for cash_id {cash_id}', 'order_id': cash_transaction.id})

        return messages
        

    @api.model
    def create(self, vals):
        record = super(CashTransactionsWags, self).create(vals)
        sequence_num = self.env['ir.sequence'].next_by_code('cash.transactions.sequence')
        if not sequence_num:
            raise ValidationError("Please ensure that the sequence for Cash Transaction is set up correctly in the configuration")
        record.reference = sequence_num
        return record


    """ Block deletion """
    def unlink(self):
        for rec in self:
            raise ValidationError('You cannot delete this record')
            super(CashTransactionsWags, self).unlink()
            return True


class PosSessionWagsExt(models.Model):
    _inherit = 'pos.session.wags'

    cash_transaction_ids = fields.One2many('cash.transactions.wags','pos_session_id',tracking=True)
    open_close_cash_ids = fields.One2many('cash.transactions.wags','pos_session_close_id',tracking=True)
    cash_in_move_id = fields.Many2one('account.move.wags',string="CashIn Journal Entry")
    cash_out_move_id = fields.Many2one('account.move.wags',string="CashOut Journal Entry")

    def fetch_cash_transactions(self):
        self.cash_in = 0
        self.cash_out = 0
        for rec in self.cash_transaction_ids:
            rec.pos_session_id = False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Open Cash Transactions',
            'res_model': 'cash.transactions.wags',
            'view_mode': 'tree',
            'view_type': 'tree',
            'view_id': self.env.ref('cash_transactions_wags.view_cash_transactions_wizard').id,
            'domain':[('type','in',['in','out']),('pos_session_id','=',False)],
            'context': {'session_id': self.id, 'readonly_by_pass': True},
            'target': 'new',
        }


    def fetch_open_close_transactions(self):
        self.opening_cash = 0
        self.actual_cash = 0
        for rec in self.open_close_cash_ids:
            rec.pos_session_close_id = False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Open Cash Transactions',
            'res_model': 'cash.transactions.wags',
            'view_mode': 'tree',
            'view_type': 'tree',
            'view_id': self.env.ref('cash_transactions_wags.view_cash_transactions_opening_wizard').id,
            'domain':[('type','in',['open','close']),('pos_session_close_id','=',False)],
            'context': {'session_id': self.id, 'readonly_by_pass': True},
            'target': 'new',
        }


    def create_journal_entry(self):
        res = super(PosSessionWagsExt, self).create_journal_entry()
        if self.cash_in > 0:
            self.create_cash_journal_entry("in")
        if self.cash_out > 0:
            self.create_cash_journal_entry("out")
        return res

    def update_cash_amount(self):
        cash_in = 0
        cash_out = 0
        for rec in self.cash_transaction_ids:
            if rec.type == 'in':
                cash_in += rec.amount
            if rec.type == 'out':
                cash_out += rec.amount
        self.cash_in = cash_in
        self.cash_out = cash_out

    def update_open_close_amount(self):
        self.opening_cash = sum(self.open_close_cash_ids.search([('pos_session_close_id','=',self.id),('type','=','open')],limit=1,order='id asc').mapped('amount'))
        self.actual_cash = sum(self.open_close_cash_ids.search([('pos_session_close_id','=',self.id),('type','=','close')],limit=1,order='id desc').mapped('amount'))

    def create_cash_journal_entry(self,cash_type):
        line_ids = []
        line_ids.append(
                (0, 0, {
                    'account_id': self.cash_account_id.id,
                    'analytic_account_id': self.branch_id.analytic_id.id,
                    # 'partner_id': line.partner_id.id,
                    'name': "POS Sales - " + str(self.date),
                    'date': self.date,
                    'debit': self.cash_in if cash_type == "in" else 0,
                    'credit': self.cash_out if cash_type == "out" else 0,
                })
            )

        for line in self.cash_transaction_ids.search([('type','=',cash_type),('pos_session_id','=',self.id)]):
            line_ids.append(
                    (0, 0, {
                        'account_id': line.account_id.id,
                        'analytic_account_id': self.branch_id.analytic_id.id,
                        # 'partner_id': line.partner_id.id,
                        'name': "Cash In For - " + str(self.date),
                        'date': self.date,
                        'credit': line.amount if cash_type == "in" else 0,
                        'debit': line.amount if cash_type == "out" else 0,
                    })
                )

        if cash_type == "in":
            if not self.cash_in_move_id:
                create_journal_entry = {
                    'date': self.date,
                    'source': "Closing Cash In for POS Session" + str(self.date),
                    'source_id': self.id,
                    'source_model': 'pos.session.wags',
                    'ref' : "Closing Cash In for POS Session" + str(self.date),
                    'line_ids' : line_ids,
                }
                move = self.env['account.move.wags'].create(create_journal_entry)
                self.cash_in_move_id = move.id

            else:
                self.cash_in_move_id.button_draft()
                self.cash_in_move_id.line_ids.unlink()
                self.cash_in_move_id.date = self.date
                self.cash_in_move_id.source = "POS"
                self.cash_in_move_id.ref = "POS Sales Cash In Entry" + str(self.date)
                self.cash_in_move_id.write({'line_ids': line_ids})
        else:
            if not self.cash_out_move_id:
                create_journal_entry = {
                    'date': self.date,
                    'source': "Closing Cash Out for POS Session" + str(self.date),
                    'source_id': self.id,
                    'source_model': 'pos.session.wags',
                    'ref' : "Closing Cash Out for POS Session" + str(self.date),
                    'line_ids' : line_ids,
                }
                move = self.env['account.move.wags'].create(create_journal_entry)
                self.cash_out_move_id = move.id

            else:
                self.cash_out_move_id.button_draft()
                self.cash_out_move_id.line_ids.unlink()
                self.cash_out_move_id.date = self.date
                self.cash_out_move_id.source = "POS"
                self.cash_out_move_id.ref = "POS Sales Cash Out Entry" + str(self.date)
                self.cash_out_move_id.write({'line_ids': line_ids})


class CashTypeWags(models.Model):
    _name = 'cash.type.wags'
    _description = "Cash Type"

    name = fields.Char(string="Name")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)


class CashClosingWagsExt(models.Model):
    _inherit = "cash.closing.wags"

    opening_cash_id = fields.Many2one('cash.transactions.wags', string="Opening Cash",tracking=True, required=True)
    opening_datetime = fields.Datetime(string="Opening Datetime", tracking=True, compute="_compute_opening_datetime")
    closing_cash_id = fields.Many2one('cash.transactions.wags', string="Closing Cash",tracking=True, required=True)
    closing_datetime = fields.Datetime(string="Closing Datetime", tracking=True, compute="_compute_closing_datetime")
    account_id = fields.Many2one("account.account.wags", string="Account", tracking=True)
    pay_in_account_id = fields.Many2one('account.account.wags',string="Pay In Account")
    pay_out_account_id = fields.Many2one('account.account.wags',string="Pay Out Account")
    cash_difference_entry = fields.Many2one("account.move.wags", string="Cash Difference Entry", tracking=True)
    cashin_journal_id = fields.Many2one("account.move.wags", string="Cash In Journal Entry", tracking=True)
    cashout_journal_id = fields.Many2one("account.move.wags", string="Cash Out Journal Entry", tracking=True)


    def action_draft(self):
        if self.state != 'draft':
            self.closing_cash_id.cash_closing_id = False
            self.opening_cash_id.cash_closing_id = False
            if self.cash_difference_entry:
                self.cash_difference_entry.button_draft()
                self.cash_difference_entry.line_ids.unlink(permission=True)
                self.cash_difference_entry.date = self.date
            if self.cashin_journal_id:
                self.cashin_journal_id.button_draft()
                self.cashin_journal_id.line_ids.unlink(permission=True)
                self.cashin_journal_id.date = self.date
            if self.cashout_journal_id:
                self.cashout_journal_id.button_draft()
                self.cashout_journal_id.line_ids.unlink(permission=True)
                self.cashout_journal_id.date = self.date
            self.state = 'draft'


    def action_validate(self):
        if self.state != 'validate':
            # if not self.user_id:
            #     raise ValidationError("Please add session user!")
            # self.calculate_cash_values()
            # self.calculate_difference()
            self.closing_cash_id.cash_closing_id = self.id
            self.opening_cash_id.cash_closing_id = self.id
            self.create_cash_difference_entry()
            if self.cash_in > 0:
                self.create_cash_journal_entry("in")
            if self.cash_out > 0:
                self.create_cash_journal_entry("out")
            self.state = 'validate'


    @api.depends('opening_cash_id')
    def _compute_opening_datetime(self):
        for rec in self:
            rec.opening_datetime = rec.opening_cash_id.datetime if rec.opening_cash_id else False


    @api.depends('closing_cash_id')
    def _compute_closing_datetime(self):
        for rec in self:
            rec.closing_datetime = rec.closing_cash_id.datetime if rec.closing_cash_id else False


    def create_cash_journal_entry(self, cash_type):
        line_ids = []
        if cash_type == 'in':
            description = "Cash In For - "
        elif cash_type == 'out':
            description = "Cash Out For - "
        else:
            description = ""

        line_ids.append(
                (0, 0, {
                    'account_id': self.cash_account_id.id,
                    'analytic_account_id': self.branch_id.analytic_id.id,
                    'name': "POS Sales - " + str(self.date),
                    'date': self.date,
                    'debit': self.cash_in if cash_type == "in" else 0,
                    'credit': self.cash_out if cash_type == "out" else 0,
                })
            )
        line_ids.append(
                (0, 0, {
                    'account_id': self.pay_in_account_id.id if cash_type == "in" else self.pay_out_account_id.id,
                    'analytic_account_id': self.branch_id.analytic_id.id,
                    'name': str(description) + str(self.date),
                    'date': self.date,
                    'credit': self.cash_in if cash_type == "in" else 0,
                    'debit': self.cash_out if cash_type == "out" else 0,
                })
            )

        if cash_type == "in":
            if not self.cashin_journal_id:
                create_journal_entry = {
                    'date': self.date,
                    'source': "Cash Closing " + str(self.date),
                    'source_id': self.id,
                    'source_model': 'cash.closing.wags',
                    'ref' : "Cash In for POS Cash Closing " + str(self.date),
                    'line_ids' : line_ids,
                }
                move = self.env['account.move.wags'].create(create_journal_entry)
                self.cashin_journal_id = move.id

            else:
                self.cashin_journal_id.button_draft()
                self.cashin_journal_id.line_ids.unlink(permission=True)
                self.cashin_journal_id.date = self.date
                self.cashin_journal_id.source = "Cash Closing"
                self.cashin_journal_id.ref = "Cash In for POS Cash Closing" + str(self.date)
                self.cashin_journal_id.write({'line_ids': line_ids})
        else:
            if not self.cashout_journal_id:
                create_journal_entry = {
                    'date': self.date,
                    'source': "Cash Closing" + str(self.date),
                    'source_id': self.id,
                    'source_model': 'cash.closing.wags',
                    'ref' : "Cash Out for POS Cash Closing" + str(self.date),
                    'line_ids' : line_ids,
                }
                move = self.env['account.move.wags'].create(create_journal_entry)
                self.cashout_journal_id = move.id

            else:
                self.cashout_journal_id.button_draft()
                self.cashout_journal_id.line_ids.unlink(permission=True)
                self.cashout_journal_id.date = self.date
                self.cashout_journal_id.source = "Cash Closing"
                self.cashout_journal_id.ref = "Cash Out for POS Cash Closing" + str(self.date)
                self.cashout_journal_id.write({'line_ids': line_ids})


    def create_cash_difference_entry(self):
        line_ids = []
        if not self.company_id.cash_diff_account_id:
            raise ValidationError("Please configure cash difference account.")

        branch = self.env['branch.wags'].search([('branch_user_ids', 'in', self.env.user.id)])
        if branch:
            cash_accounts = branch.account_ids.filtered(lambda acc: acc.type == 'cash')

            if len(cash_accounts) > 1:
                raise ValidationError("Multiple cash accounts found. Please configure only one cash account per branch.")

            if not cash_accounts:
                raise ValidationError("No cash account found for the branch.")

            if self.company_id.allow_pos_payment_method:
                payment_methods = branch.payment_method_ids.filtered(lambda method: method.is_cash == True)

                if len(payment_methods) > 1:
                    raise ValidationError("Multiple cash payment methods found. Please configure only one cash payment method per branch.")

                if not payment_methods:
                    raise ValidationError("No cash payment method found for the branch.")
                

        if self.cash_difference < 0:
            line_ids.append(
                (0, 0, {
                    'name':self.branch_id.reference + ' - loss',
                    'debit': abs(self.cash_difference),
                    'credit': 0,
                    'account_id': self.cash_account_id.id,
                    'analytic_account_id': self.branch_id.analytic_id.id,
                    # 'analytic_tag_ids': self.analytic_tag_ids.ids,
                    'date':self.date,
                    })) 
            line_ids.append(
                (0, 0, {
                    'name': self.branch_id.reference + ' - loss',
                    'credit': abs(self.cash_difference),
                    'debit': 0,
                    'account_id': self.company_id.cash_diff_account_id.id,
                    'analytic_account_id': self.branch_id.analytic_id.id,
                    # 'analytic_tag_ids': self.analytic_tag_ids.ids,
                    'date':self.date,
                    })) 
            if not self.cash_difference_entry:
                create_journal_entry = {
                    'name': "Loss",
                    'line_ids': line_ids,
                    'date': self.date,
                    'source': 'Cash Closing',
                    'source_id': self.id,
                    'source_model': 'cash.closing.wags',
                    'ref': self.branch_id.reference + ' - loss',
                }
                move = self.env['account.move.wags'].create(create_journal_entry)
                self.cash_difference_entry = move.id

            else:
                self.cash_difference_entry.button_draft()
                self.cash_difference_entry.line_ids.unlink(permission=True)
                self.cash_difference_entry.date = self.date
                self.cash_difference_entry.ref = self.branch_id.reference + ' - loss'
                self.cash_difference_entry.source =  'Cash Closing'
                self.cash_difference_entry.write({'line_ids': line_ids})

        if self.cash_difference > 0:

            line_ids.append(
                (0, 0, {
                    'name': self.branch_id.reference + ' - profit',
                    'credit': self.cash_difference,
                    'debit': 0,
                    'account_id': self.cash_account_id.id,
                    'analytic_account_id': self.branch_id.analytic_id.id,
                    # 'analytic_tag_ids': self.analytic_tag_ids.ids,
                    'date':self.date,
                    })) 
            line_ids.append(
                (0, 0, {
                    'name': self.branch_id.reference + ' - profit',
                    'debit': self.cash_difference,
                    'credit': 0,
                    'account_id': self.company_id.cash_diff_account_id.id,
                    'analytic_account_id': self.branch_id.analytic_id.id,
                    # 'analytic_tag_ids': self.analytic_tag_ids.ids,
                    'date':self.date,
                    })) 

            if not self.cash_difference_entry:
                create_journal_entry = {
                    'name': "Profit",
                    'line_ids': line_ids,
                    'date': self.date,
                    'source': 'Cash Closing',
                    'source_id': self.id,
                    'source_model': 'cash.closing.wags',
                    'ref': self.branch_id.reference + ' - profit',
                }
                move = self.env['account.move.wags'].create(create_journal_entry)
                self.cash_difference_entry = move.id
            else:
                self.cash_difference_entry.button_draft()
                self.cash_difference_entry.line_ids.unlink(permission=True)
                self.cash_difference_entry.date = self.date
                self.cash_difference_entry.ref = self.branch_id.reference + ' - profit'
                self.cash_difference_entry.source = 'Cash Closing'
                self.cash_difference_entry.write({'line_ids': line_ids})