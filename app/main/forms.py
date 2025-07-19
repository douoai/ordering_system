from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange, Length

class UserInfoForm(FlaskForm):
    """用户信息表单 - 简化版，只需要用户名和电话"""
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=80)])
    phone = StringField('电话', validators=[DataRequired(), Length(min=11, max=20)],
                       render_kw={"placeholder": "请输入手机号"})
    quantity = IntegerField('数量', validators=[DataRequired(), NumberRange(min=1, max=20)], default=1,
                           render_kw={"placeholder": "请选择数量"})
    submit = SubmitField('开始下单')

class OrderForm(FlaskForm):
    """下单表单"""
    drink_product_id = SelectField('选择饮品', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('数量', validators=[DataRequired(), NumberRange(min=1, max=20)], default=1)
    temperature = SelectField('温度', choices=[('hot', '热'), ('ice', '冰'), ('room', '常温')], validators=[DataRequired()])
    item_notes = TextAreaField('特殊要求', validators=[Length(max=200)])
    notes = TextAreaField('订单备注', validators=[Length(max=500)])
    submit = SubmitField('提交订单')
