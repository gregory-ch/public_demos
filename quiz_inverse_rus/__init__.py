from otree.api import *


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'quiz_inverse_rus'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    single=[       'q_2',
                   'q_4',
                   'q_6',
                   'q_7',
                   'q_8']
    multipple_1=['q_1', 'q_1_2', 'q_1_3', 'q_1_4', 'q_1_5']   
    multipple_2=['q_3', 'q_3_2', 'q_3_3', 'q_3_4', 'q_3_5']
    multipple_3=['q_5', 'q_5_2', 'q_5_3']

class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    q_1 = models.StringField(
        # choices=["Да", "Нет"],
        label='a.   На Y в этой строке (клумбе) влияет другое сильное незрелое Z=0',
        # widget=widgets.CheckboxSelectMultiple,
        )

    q_1_2 = models.StringField(blank=True,
        # choices=["Да", "Нет"],
        label="b.   На Y в этой строке (клумбе) влияет другое сильное незрелое Z=1",)

    q_1_3 = models.StringField(
        # choices=["Да", "Нет"],
        label='c.   Строка (клумба) находится на каменистой почве',)

    q_1_4 = models.StringField(blank=True,
        # choices=["Да", "Нет"],
        label="d.   Значение на отдельной клумбе может выпасть случайно",)

    q_1_5 = models.StringField(blank=True,
        # choices=["Да", "Нет"],
        label="e.   Строка (клумба) находится на песчаной почве",)

    q_2 = models.StringField(
        choices=["12",
                 "16",
                 "8"],
        label='2.   ' + '{:s}'.format('\u0332'.join(
              'Сколько из 16 клумб могут быть на каменистой почве?\n')),
        widget=widgets.RadioSelect)

    q_3 = models.StringField(blank=True,
        # choices=["Верно", "Неверно"],
        label='a.   X=1 в первой клумбе (строке) может изменить состояние незрелого Y, изначально равного 0, на Y=1',)

    q_3_2 = models.StringField(blank=True,
        # choices=["Верно", "Неверно"],
        label='b.   X=0 может в первой клумбе (строке) изменить состояние зрелого Y изначально равного 1 на Y=0',)

    q_3_3 = models.StringField(
        # choices=["Верно", "Неверно"],
        label='c.   X=1 может в первой клумбе (строке) изменить состояние незрелого' + 
        'Y изначально равного 0 на Y=1 и одновременно X=1 может во второй клумбе/строке изменить состояние зрелого Y изначально равное 1 на Y=0',
        sanitize_html=False,)

    q_3_4 = models.StringField(
        # choices=["Верно", "Неверно"],
        label='d.   X=1 может в первой клумбе (строке) изменить состояние зрелого Y изначально равного 1 на Y=0',)

    q_3_5 = models.StringField(
        # choices=["Верно", "Неверно"],
        label='e.   X=0 может в первой клумбе (строке) изменить состояние незрелого Y изначально равного 1 на Y=0',)

    q_4 = models.StringField(
        choices=["Оно незрелое (свойство самого Y)",
                 "Оно слабое (Влияние другого сильного не зрелого Семени)",
                 "Оно не зрелое и/или слабое"],
        label='4.   ' + '{:s}'.format('\u0332'.join(
            'Назовите ВСЕ возможные причины того, что семя Y не проросло:\n')),
        widget=widgets.RadioSelect)

    q_5 = models.StringField(
        # choices=['Корректно', 'Некорректно'],
        label= 'a.   X слабое и Y сильное',)

    q_5_2 = models.StringField(blank=True,
        # choices=['Корректно', 'Некорректно'],
        label='b.   X сильное и Y слабое',)

    q_5_3 = models.StringField(
        # choices=['Корректно', 'Некорректно'],
        label='с.   X не сильное и не слабое Y не сильное и не слабое',)

    q_6 = models.StringField(
        choices=["Z🡢Y, Y🡢X, X🡢Y",
                 "Z🡢Y, X🡢Y, X🡢Z",
                 "X🡢Y, X🡢Z, Y🡢X"],
        label='6.   ' + '{:s}'.format('\u0332'.join(
              'Если уже известно, что Y сильное по отношению к Z, а Z cильное по отношению к X выберете пункт, в котором перечислены ВСЕ связи между сильными и слабыми семенами, которых НЕ МОЖЕТ БЫТЬ:\n')),
        widget=widgets.RadioSelect)

    q_7 = models.StringField(
        choices=["прорастёт если оно зрелое",
                 "прорастёт если оно не на каменистой почве",
                 "не прорастёт если оно на песчаной почве "],
        label='7.   ' + '{:s}'.format('\u0332'.join(
              'Завершите фразу корректно: нейтральное (не сильное и не слабое) семя...\n')),
        widget=widgets.RadioSelect)

    q_8 = models.StringField(
        choices=["каменистые почвы находятся в клумбах с такими же номерами",
                 "количество сильных и слабых связей одинаково, но разные типы семян могут быть сильными или слабыми в сравнении с оригинальной планетой",
                 "то же количество зрелых семян посажено на каменистых почвах, что и на планете оригинале"],
        label='8.   ' + '{:s}'.format('\u0332'.join(
              'Завершите фразу корректно: на планете двойнике...\n')),
        widget=widgets.RadioSelect)


# PAGES

class Instruction(Page):
    pass

class Quiz(Page):

    form_model = 'player'
    form_fields = C.single+C.multipple_1+C.multipple_2+C.multipple_3
    
    @staticmethod
    def error_message(player, values):
        #print('values is', values)
        if (values['q_1'] != '1' or
            values['q_1_2'] != "" or #
            values['q_1_3'] != '1' or
            values['q_1_4'] != "" or #
            values['q_1_5'] != "" or #

            values['q_2'] != "8" or

            values['q_3'] != '' or #
            values['q_3_2'] != '' or #
            values['q_3_3'] != '1' or
            values['q_3_4'] != '1' or
            values['q_3_5'] != '1' or

            values['q_4'] != "Оно не зрелое и/или слабое" or

            values['q_5'] != '1' or
            values['q_5_2'] != '' or #
            values['q_5_3'] != '1' or

            values['q_6'] != "Z🡢Y, X🡢Y, X🡢Z" or

            values['q_7'] != "прорастёт если оно зрелое" or

            values['q_8'] != "то же количество зрелых семян посажено на каменистых почвах, что и на планете оригинале"
        ):
            return 'пожалуйста исправьте некорректные ответы'



class MyPage1(Page):
    #form_model = 'player'
    #form_fields = ['Aot_' + str(x + 1) for x in range(7)] + ['Age']
    pass



page_sequence = [Instruction, Quiz]
