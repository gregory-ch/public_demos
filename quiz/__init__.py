from otree.api import *

doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'quiz'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    Aot_1 = models.StringField(
        choices=["Семена не растут.", "Не растут незрелые и слабые незрелые семена.",
                 "Не растут только слабые семена."],
        label='На каменистых почвах',
        widget=widgets.RadioSelectHorizontal)

    Aot_2 = models.StringField(
        choices=["12", "16", "8"],
        label='Сколько из 16 клумб могут быть на каменистой почве?',
        widget=widgets.RadioSelectHorizontal)

    Aot_3 = models.StringField(
        choices=['Оно незрелое', 'Оно слабое', 'Оно не зрелое и/или слабое'],
        label='Назовите все возможные причины того, что семя не проросло.',
        widget=widgets.RadioSelectHorizontal)

    Aot_4 = models.StringField(
        choices=["X слабое и Y сильное.", "X сильное и Y слабое.", "X не сильное и не слабое Y сильное.", "X не сильное и не слабое Y не сильное и не слабое."],
        label='Рассмотрим упрощённую задачу, где продемонстрированы наблюдения только 2-х типов семян, расположенных только над песчаными почвами, и все зрелые семена известны и помечены оранжевым цветом. Тогда зависимости между типами семян будут:',
        widget=widgets.RadioSelectHorizontal)

    Aot_5 = models.StringField(
        choices=['Семя Y на клумбе 7 проросло на планете близнеце (справа), потому что оно сильное.', 'Семя Y на клумбе 7 не проросло на планете (слева), потому что оно слабое.', 'Семя Y на клумбе 3 не проросло, потому что оно на каменистой почве, оно слабое и незрелое.'],
        label='Рассмотрим теперь, точно такие же наблюдения, но два отличия приближают их обратно к не упрощённому заданию. Первое: зрелые семена так же расположены по тем же номерам клумб, но больше нет выделения цветом. Второе: клумба №1 в таблице слева и клумба №3 в таблице справа теперь находятся на каменистых почвах. Обратите внимание, что хоть номера клумб и не совпадают, количество зрелых семян, распределённое по каменистым клумбам всегда одинаковое на обоих планетах. Выберете правильное утверждение:',
        widget=widgets.RadioSelectHorizontal)

    Aot_6 = models.StringField(
        choices=['Z->Y, Y->X, X->Y', 'Z->Y, X->Y, X->Z', 'X->Y, X->Z, Y->X'],
        label='Если уже известно, что Y сильное по отношению к Z, а Z cильное по отношению к X выберете пункт, в котором перечислены вся связи между сильными и слабыми семенами, которых не может быть:',
        widget=widgets.RadioSelectHorizontal)

    Aot_7 = models.StringField(
        choices=["прорастёт если оно зрелое", "прорастёт если оно не на каменистой почве", "не прорастёт если оно на песчаной почве"],
        label='Завершите фразу корректно: нейтральное (не сильное и не слабое) семя:',
        widget=widgets.RadioSelectHorizontal)

    Aot_8 = models.StringField(
        choices=["Каменистые почвы находятся в клумбах с такими же номерами", "Количество сильных и слабых связей одинаково, но разные типы семян могут быть сильными или слабыми в сравнении с оригинальной планетой",
                 "То же количество зрелых семян посажено на каменистых почвах, что и на планете оригинале"],
        label='Завершите фразу корректно: на планете двойнике',
        widget=widgets.RadioSelectHorizontal)

    Age = models.IntegerField(
        min=14, max=90,
        label='Укажите возраст участника')

    feedback1 = models.StringField(label="Общие пожелания и комментарии")

    feedback2 = models.StringField(label="Были ли понятны инструкции? Если нет, то что было непонятно?")

    feedback3 = models.StringField(
        label="Считаете ли вы что между двумя таблицами (данные с оригинальной планетой и планеты близнеца соответственно) есть разница, если да то в чём?")

    feedback4 = models.StringField(label="Какова была Ваша стратегия при выборе ответов?")

    feedback5 = models.StringField(
        label="Были ли понятно, что данные с планеты двойника идентичны данным, которые бы можно было получить, проведя на оригинальной планете эксперимент (пересадить часть семян)? (да/нет, что было непонятно?)")

    feedback6 = models.StringField(label="Было ли понятно, что нас интересуют причинно-следственные связи?")
    #
    # Aot_5 = models.IntegerField(
    #     min=1, max=5,
    #     choices=[0, 1, 2, 3, 4, 5],
    #     label='Менять свое мнение — признак слабости.',
    #     widget=widgets.RadioSelectHorizontal)
    #
    # Aot_6 = models.IntegerField(
    #     min=1, max=5,
    #     choices=[0, 1, 2, 3, 4, 5],
    #     label='Людям следует активно искать причины, по которым они могут оказаться неправы.',
    #     widget=widgets.RadioSelectHorizontal)
    #
    # Aot_7 = models.IntegerField(
    #     min=1, max=5,
    #     choices=[0, 1, 2, 3, 4, 5],
    #     label='Можно не учитывать свидетельства против убеждений, в которых уверен(а).',
    #     widget=widgets.RadioSelectHorizontal)
    #
    # Aot_8 = models.IntegerField(
    #     min=1, max=5,
    #     choices=[0, 1, 2, 3, 4, 5],
    #     label='Важно придерживаться своих убеждений, даже когда предоставлены свидетельства, говорящие об обратном.',
    #     widget=widgets.RadioSelectHorizontal)
    #
    # Aot_9 = models.IntegerField(
    #     min=1, max=5,
    #     choices=[0, 1, 2, 3, 4, 5],
    #     label='Правильное мышление, в случае если есть хорошие аргументы за обе стороны, приводит к нерешительности.',
    #     widget=widgets.RadioSelectHorizontal)
    #
    # Aot_10 = models.IntegerField(
    #     min=1, max=5,
    #     choices=[0, 1, 2, 3, 4, 5],
    #     label='Прежде чем принимать решение по поводу сложного вопроса, нужно рассмотреть больше одного возможного варианта ответа.',
    #     widget=widgets.RadioSelectHorizontal)
    #
    # Aot_11 = models.IntegerField(
    #     min=1, max=5,
    #     choices=[0, 1, 2, 3, 4, 5],
    #     label='Лучше быть уверенным в умозаключении даже если есть веские причины сомневаться в нем.',
    #     widget=widgets.RadioSelectHorizontal)


# PAGES
class MyPage1(Page):
    form_model = 'player'
    form_fields = ['Aot_' + str(x + 1) for x in range(8)]


class MyPage2(Page):
    form_model = 'player'
    form_fields = ['feedback' + str(x + 1) for x in range(6)]


class ResultsWaitPage(WaitPage):
    pass


class Results(Page):
    pass


page_sequence = [MyPage1]
