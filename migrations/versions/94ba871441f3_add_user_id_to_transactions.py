"""Add user_id to transactions

Revision ID: 94ba871441f3
Revises: 56535657aab5
Create Date: 2025-03-17 02:05:12.887635

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '94ba871441f3'
down_revision = '56535657aab5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('details', sa.Text(), nullable=True))
        batch_op.alter_column('user_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
        batch_op.alter_column('action',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=10),
               type_=sa.String(length=50),
               existing_nullable=False)

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key(None, 'users', ['user_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.alter_column('action',
               existing_type=sa.String(length=50),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=10),
               existing_nullable=False)
        batch_op.alter_column('user_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
        batch_op.drop_column('details')

    # ### end Alembic commands ###
