import random
from otree.api import *
import json

"""
typing game setup: random string of 1 and 0 for a few seconds, type the string immediately.
+1 point per correct character, -1 point per incorrect character.
-20 points if they make 4 or more mistakes in a round. 
"""

class C(BaseConstants):
    NAME_IN_URL = 'typing_game'
    PLAYERS_PER_GROUP = None
    MAIN = 5 # number of rounds for the main game for creating subsession function
    ASSESSMENT = 5 # number of rounds for each assessment block 
    ASSESSMENT_BLOCKS = 4 # number of assessment blocks

    NUM_ROUNDS = MAIN + (ASSESSMENT * ASSESSMENT_BLOCKS)
    TIME_LIMIT = 1000  # in milliseconds
    TYPE_TIME_LIMIT = 3000  # in milliseconds
    CORRECT = 1
    MISTAKE = -1
    MISTAKE_THRESHOLD = 4
    THRESHOLD_PENALTY = -20

    
#participation fee
    PARTICIPATION_FEE = 0.50
    BONUS = 0.1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    #choice = models.StringField(choices = ['play', 'safe'], blank=True)
    string_length = models.IntegerField() 
    phase = models.StringField() #assessment and main
    target_string = models.StringField()
    typed_string = models.StringField(blank=True)
    correct = models.IntegerField(initial=0)
    mistakes = models.IntegerField(initial=0)
    round_score = models.IntegerField(initial=0)
    keystroke_time = models.LongStringField(blank=True)
    round_keystroke_time = models.IntegerField(initial=0) #in ms
    total_keystroke_time = models.IntegerField(initial=0)
    
    #demographics 
    age = models.IntegerField(blank=True, min=18, max=100)
    gender = models.StringField(choices=['Male', 'Female', 'Other'])
    prolific_id = models.StringField(blank=True)


def creating_session(subsession: Subsession):
    for p in subsession.get_players():
        #generate and shuffle blocks
        if subsession.round_number == 1:
            block_lengths = [5, 7, 9, 11] #same length as ASSESSMENT_BLOCKS
            random.shuffle(block_lengths)
            subsession.session.vars['block_lengths'] = block_lengths

            #build assessment sequences
            sequence = []
            for length in block_lengths:
                sequence.extend([length] * 5)  # 5 rounds of each length

            p.participant.vars['assessment_lengths'] = sequence

        #assign main phase
        if subsession.round_number <= C.MAIN:
            p.string_length = 10
            p.phase = 'main'
        #assign assessment phase 
        else:
            assessment_index = subsession.round_number - C.ASSESSMENT - 1 #maps rounds to indices 0 - 20
            #######remember that you have cluged these indices 
            p.string_length = p.participant.vars['assessment_lengths'][assessment_index]
            p.phase = 'assessment'
        #generate target string
        p.target_string = ''.join(
                random.choice('10') for _ in range(p.string_length)
            )
    

def calculate_score(player: Player):
    target = player.target_string
    typed = player.typed_string or ''

    correct = 0
    mistakes = 0

    for i in range(max(len(target), len(typed))):
        target_ch = target[i] if i < len(target) else None
        typed_ch = typed[i] if i < len(typed) else None

        if typed_ch == target_ch:
            correct += 1
        else:
            mistakes += 1
    points = correct * C.CORRECT + mistakes * C.MISTAKE
    if mistakes >= C.MISTAKE_THRESHOLD:
        points += C.THRESHOLD_PENALTY

    player.correct = correct
    player.mistakes = mistakes
    player.round_score = points

    # --- KEYSTROKE TIME CALCULATIONS ---
    if player.keystroke_time:
        try:
            times = json.loads(player.keystroke_time)
            if times:
                # Last value in array is total elapsed time from 1st to last keystroke
                player.round_keystroke_time = times[-1]
        except json.JSONDecodeError:
            player.round_keystroke_time = 0

    # Sum round times for all rounds up to the current one
    player.total_keystroke_time = sum(
        p.round_keystroke_time for p in player.in_all_rounds()
    )

# PAGES
class Introduction(Page):
    @staticmethod
    def is_displayed(player):
            return player.round_number == 1
    form_model = 'player'
    form_fields = ['age', 'gender', 'prolific_id']
    @staticmethod
    def vars_for_template(player):
        return {
            'participation_fee': C.PARTICIPATION_FEE
        }
    
class Instructions(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1
    @staticmethod
    def vars_for_template(player):
        return {
            'num_rounds': C.NUM_ROUNDS,
            'time_limit': C.TIME_LIMIT // 1000,  # convert to seconds
            'type_time_limit': C.TYPE_TIME_LIMIT // 1000,  # convert to seconds
            'string_length': player.string_length,
            'correct_points': C.CORRECT,
            'mistake_points': C.MISTAKE,
            'mistake_threshold': C.MISTAKE_THRESHOLD,
            'threshold_penalty': C.THRESHOLD_PENALTY,
            'participation_fee': C.PARTICIPATION_FEE,
            'bonus': C.BONUS
        }

class Choice(Page):
    form_model = 'player'
    form_fields = ['choice']

class Ready(Page):
    pass
    
    
class Game(Page):
    form_model = 'player'
    form_fields = ['typed_string', 'keystroke_time']

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        calculate_score(player)

class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        total_score = sum(p.round_score for p in player.in_all_rounds())
        return {
           'total_score': total_score,
           'is_last_round': player.round_number == C.NUM_ROUNDS
        }

page_sequence = [Instructions, Ready, Game, Results]
