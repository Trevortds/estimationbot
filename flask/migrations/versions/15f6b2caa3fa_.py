"""empty message

Revision ID: 15f6b2caa3fa
Revises: 
Create Date: 2018-08-17 16:56:25.866432

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '15f6b2caa3fa'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('answer',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('team', sa.String(length=64), nullable=True),
    sa.Column('issue_id', sa.Integer(), nullable=True),
    sa.Column('user_name', sa.String(length=64), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_answer_issue_id'), 'answer', ['issue_id'], unique=False)
    op.create_index(op.f('ix_answer_team'), 'answer', ['team'], unique=False)
    op.create_index(op.f('ix_answer_user_name'), 'answer', ['user_name'], unique=False)
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('channel', sa.String(length=32), nullable=True),
    sa.Column('user_name', sa.String(length=64), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_channel'), 'user', ['channel'], unique=True)
    op.create_index(op.f('ix_user_user_name'), 'user', ['user_name'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_user_user_name'), table_name='user')
    op.drop_index(op.f('ix_user_channel'), table_name='user')
    op.drop_table('user')
    op.drop_index(op.f('ix_answer_user_name'), table_name='answer')
    op.drop_index(op.f('ix_answer_team'), table_name='answer')
    op.drop_index(op.f('ix_answer_issue_id'), table_name='answer')
    op.drop_table('answer')
    # ### end Alembic commands ###
