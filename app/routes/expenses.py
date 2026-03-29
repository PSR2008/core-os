"""
app/routes/expenses.py — Wallet with pagination.
Previously loaded all expenses with .all() — replaced with paginated query.
"""
from datetime import date
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.expense import Expense
from app.services.game_service import user_stats, shared_ctx
from app.services.growth_service import track
from . import Blueprint

expenses_bp = Blueprint('expenses', __name__)
PAGE_SIZE = 30   # expenses per page


@expenses_bp.route('/expenses', methods=['GET', 'POST'], endpoint='expenses')
@login_required
def expenses():
    u = current_user
    if request.method == 'POST':
        category = request.form.get('category', '').strip()[:80]
        raw      = request.form.get('amount', '').strip()
        if not category:
            flash('Select or enter a category.', 'error')
        elif not raw:
            flash('Enter an amount.', 'error')
        else:
            try:
                amount = float(raw)
                if amount <= 0:
                    flash('Amount must be greater than zero.', 'error')
                elif amount > 10_000_000:
                    flash('Amount exceeds maximum allowed.', 'error')
                else:
                    db.session.add(Expense(
                        user_id=u.id, category=category,
                        amount=round(amount, 2), date=date.today(),
                    ))
                    db.session.commit()
                    track('expense_log', user_id=u.id)
                    flash(f'{amount:,.2f} logged under {category}.', 'success')
            except ValueError:
                flash('Invalid amount — numbers only.', 'error')
        return redirect(url_for('expenses.expenses'))

    try:
        page = max(int(request.args.get('page', 1)), 1)
    except (ValueError, TypeError):
        page = 1
    offset     = (page - 1) * PAGE_SIZE
    total      = Expense.query.filter_by(user_id=u.id).count()
    pages      = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    ledger     = (Expense.query.filter_by(user_id=u.id)
                  .order_by(Expense.id.desc())
                  .limit(PAGE_SIZE).offset(offset).all())

    return render_template('expenses.html',
        ledger=ledger, page=page, pages=pages, total=total,
        **user_stats(u), **shared_ctx(u))


@expenses_bp.route('/update_budget', methods=['POST'], endpoint='update_budget')
@login_required
def update_budget():
    u   = current_user
    raw = request.form.get('budget', '').strip()
    if not raw:
        flash('Enter a budget amount.', 'error')
    else:
        try:
            new_budget = float(raw)
            if new_budget < 0:
                flash('Budget cannot be negative.', 'error')
            else:
                u.budget = round(new_budget, 2)
                db.session.commit()
                flash(f'Monthly budget updated to {new_budget:,.2f}.', 'success')
        except ValueError:
            flash('Invalid budget value.', 'error')
    return redirect(url_for('expenses.expenses'))


@expenses_bp.route('/delete/expenses/<int:id>', methods=['POST'], endpoint='delete_expense')
@login_required
def delete_expense(id):
    exp = Expense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(exp)
    db.session.commit()
    flash('Expense record purged.', 'info')
    return redirect(request.referrer or url_for('expenses.expenses'))
