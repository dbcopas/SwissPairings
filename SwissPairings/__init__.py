import logging
import random
import bitarray
from enum import Enum
import azure.functions as func

new_game_form = """<!DOCTYPE html>
    <html>
    <body>
    <h2>New Game</h2>
    <form action="http://localhost:7071/SwissPairings" method="POST">
        Number of Players<br>
        <input type="text" name="pnum">
        <br>
        Number of Rounds<br>
        <input type="text" name="rnum">
        <br>
        <br><br>
        <button type="submit">Submit</button>
    </form>
    </body>
    </html>"""

symbols = {
                '0' : bitarray.bitarray('000000'),
                '1' : bitarray.bitarray('000001'),
                '2' : bitarray.bitarray('000010'),
                '3' : bitarray.bitarray('000011'),
                '4' : bitarray.bitarray('000100'),
                '5' : bitarray.bitarray('000101'),
                '6' : bitarray.bitarray('000110'),
                '7' : bitarray.bitarray('000111'),
                '8' : bitarray.bitarray('001000'),
                '9' : bitarray.bitarray('001001'),
                'a' : bitarray.bitarray('001010'),
                'b' : bitarray.bitarray('001011'),
                'c' : bitarray.bitarray('001100'),
                'd' : bitarray.bitarray('001101'),
                'e' : bitarray.bitarray('001110'),
                'f' : bitarray.bitarray('001111'),
                'g' : bitarray.bitarray('010000'),
                'h' : bitarray.bitarray('010001'),
                'i' : bitarray.bitarray('010010'),
                'j' : bitarray.bitarray('010011'),
                'k' : bitarray.bitarray('010100'),
                'l' : bitarray.bitarray('010101'),
                'm' : bitarray.bitarray('010110'),
                'n' : bitarray.bitarray('010111'),
                'p' : bitarray.bitarray('011000'),
                'q' : bitarray.bitarray('011001'),
                'r' : bitarray.bitarray('011010'),
                's' : bitarray.bitarray('011011'),
                't' : bitarray.bitarray('011100'),
                'u' : bitarray.bitarray('011101'),
                'v' : bitarray.bitarray('011110'),
                'w' : bitarray.bitarray('011111'),
                'x' : bitarray.bitarray('100000'),
                'y' : bitarray.bitarray('100001'),
                'z' : bitarray.bitarray('100010'),
                'A' : bitarray.bitarray('100011'),
                'B' : bitarray.bitarray('100100'),
                'C' : bitarray.bitarray('100101'),
                'D' : bitarray.bitarray('100110'),
                'E' : bitarray.bitarray('100111'),
                'F' : bitarray.bitarray('101000'),
                'G' : bitarray.bitarray('101001'),
                'H' : bitarray.bitarray('101010'),
                'J' : bitarray.bitarray('101011'),
                'K' : bitarray.bitarray('101100'),
                'L' : bitarray.bitarray('101101'),
                'M' : bitarray.bitarray('101110'),
                'N' : bitarray.bitarray('101111'),
                'P' : bitarray.bitarray('110000'),
                'Q' : bitarray.bitarray('110001'),
                'R' : bitarray.bitarray('110010'),
                'S' : bitarray.bitarray('110011'),
                'T' : bitarray.bitarray('110100'),
                'U' : bitarray.bitarray('110101'),
                'V' : bitarray.bitarray('110110'),
                'W' : bitarray.bitarray('110111'),
                'X' : bitarray.bitarray('111000'),
                'Y' : bitarray.bitarray('111001'),
                'Z' : bitarray.bitarray('111010'),
                '*' : bitarray.bitarray('111011'),
                '(' : bitarray.bitarray('111100'),
                '!' : bitarray.bitarray('111101'),
                ')' : bitarray.bitarray('111110'),
                '@' : bitarray.bitarray('111111'),
            }

class State:
    number_of_players = 0
    played_rounds = 0
    number_of_rounds = 0
    state_string = ""
    ordered_pairing_list = []
    players = []
    bye_player = False

    def __init__(self, state_string: str):

        self.number_of_players = 0
        self.played_rounds = 0
        self.number_of_rounds = 0
        self.state_string = ""
        self.ordered_pairing_list = []
        self.players = []
        self.bye_player = False

        if state_string is not None:
            ba = bitarray.bitarray()
            ba.encode(symbols, state_string)
            ba_string = ba.to01()
            self.number_of_players, self.number_of_rounds, self.played_rounds, self.bye_player = decode_header(ba_string) 
            self.state_string = state_string
            for i in range(self.number_of_players):
                player = Player(i)
                self.players.append(player)   
            if self.played_rounds > 0:
                width = get_player_width(self.number_of_players)
                start_index = 11
                end_index = start_index + width
                for _ in range(self.played_rounds):
                    for player in self.players:
                        opp_num = int(ba_string[start_index:end_index], 2)
                        start_index = start_index + width
                        end_index += 2
                        games_won = int(ba_string[start_index:end_index], 2)
                        player.add_result(opp_num, games_won)
                        start_index += 2
                        end_index = start_index + width
                for player in self.players:
                    player.calculate_points(self)

                ranked_player_list = self.get_ranked_players()

                if self.played_rounds < self.number_of_rounds:
                    self.ordered_pairing_list = []
                    
                    next_target = 1

                    for player in ranked_player_list:
                        player_matched = False

                        if player.player_number in self.ordered_pairing_list:
                            continue

                        while not player_matched:

                            # in case there are no possible opponents left, switch the next player not already in the rankings
                            # (which can't match with this one) with the closest higher player already in the rankings that can
                            # match with this one
                            if next_target >= self.number_of_players:
                                # get our index
                                this_player_index = next((i for i, item in enumerate(ranked_player_list) if item.player_number == player.player_number), -1)
                                # the next lower one not in the list will get swapped above us
                                possible_index = this_player_index + 1
                                no_match_yet = True
                                while no_match_yet:
                                    if ranked_player_list[possible_index].player_number in self.ordered_pairing_list:
                                        possible_index += 1
                                    else:
                                        break
                                target_to_switch = ranked_player_list[possible_index].player_number

                                # find the closest above us that would match with us
                                no_match_yet = True
                                possible_index = len(self.ordered_pairing_list) - 1
                                while no_match_yet:
                                    no_match_yet = player.player_has_played_target(self.ordered_pairing_list[possible_index])
                                    if no_match_yet:
                                        possible_index -= 1
                                    else:
                                        break
                                existing_player_to_switch = self.ordered_pairing_list[possible_index]

                                # swap them
                                for n, i in enumerate(self.ordered_pairing_list):
                                    if i == existing_player_to_switch:
                                        self.ordered_pairing_list[n] = target_to_switch

                                next_target = 1

                            if ranked_player_list[next_target].player_number in self.ordered_pairing_list \
                                or ranked_player_list[next_target].player_number == player.player_number:
                                next_target += 1
                                continue
                            if not player.player_has_played_target(ranked_player_list[next_target].player_number):
                                self.ordered_pairing_list.append(player.player_number)
                                self.ordered_pairing_list.append(ranked_player_list[next_target].player_number)
                                next_target = 1
                                player_matched = True
                            else:
                                next_target += 1
                else:
                    for player in ranked_player_list:
                        self.ordered_pairing_list.append(player.player_number)


        if self.played_rounds == 0: # create the ordered pairing list for the first round
            width = get_player_width(self.number_of_players)
            start_index = 11
            end_index = start_index + width
            for i in range(self.number_of_players):
                player_string = ba_string[start_index:end_index]
                self.ordered_pairing_list.append(int(player_string, 2))
                start_index = end_index
                end_index = start_index + width

    def get_ranked_players(self) -> list:
        return sorted(self.players, key = lambda x: (x.points, x.OMW), reverse=True)

    def build_first_state_string(self, form: dict):

        pnum = int(form['pnum'])
        rnum = int(form['rnum'])

        if pnum % 2 == 1:
            pnum += 1
            self.bye_player = True

        header = get_header(pnum, rnum, 0, self.bye_player)  

        player_numbers = []
        for i in range(pnum):
            player_numbers.append(i)    
        random.shuffle(player_numbers)
        width = get_player_width(pnum)

        for player_number in player_numbers:
            seq_header = [int(x) for x in '{:0{size}b}'.format(player_number,size=width)]
            header = header + seq_header

        header = pad_bits(header)
        ba = bitarray.bitarray(header)
        state = ba.decode(symbols)
        self.state_string = ''.join(state)

    def build_new_state_string(self):
        
        self.played_rounds = self.played_rounds + 1
        header = get_header(self.number_of_players, self.number_of_rounds, self.played_rounds, self.bye_player)
        width = get_player_width(self.number_of_players)

        for round_number in range(self.played_rounds):
            for player in self.players:
                opp_number_string = [int(x) for x in '{:0{size}b}'.format(player.rounds[round_number].opp_number,size=width)]
                header = header + opp_number_string
                games_won_string = [int(x) for x in '{:0{size}b}'.format(player.rounds[round_number].games_won,size=2)]
                header = header + games_won_string

        header = pad_bits(header)
        ba = bitarray.bitarray(header)
        state = ba.decode(symbols)
        self.state_string = ''.join(state)

    def update_history(self, form: dict):

        for k, v in form.items():
            player_nums = k.split("_")
            player_1_num = int(player_nums[0])
            player_2_num = int(player_nums[1])
            player1 = self.players[player_1_num]
            player2 = self.players[player_2_num]
            games_won_nums = v.split("_")
            player1.add_result(player_2_num, int(games_won_nums[0]))
            player2.add_result(player_1_num, int(games_won_nums[1]))
    
class Round:
    opp_number = -1
    games_won = -1
    def __init__(self, opp_number: int, games_won: int):
        self.opp_number = opp_number
        self.games_won = games_won

class Player:
    player_number = -1
    rounds = []
    points = 0
    OMW = 0

    def __init__(self, pnum:int):
        self.points = 0
        self.rounds = []
        self.player_number = pnum
        self.OMW = 0

    def add_result(self, opp_number:int, games_won: int):
        round = Round(opp_number, games_won)
        self.rounds.append(round)

    def calculate_points(self, state: State):

        if state.bye_player and (self.player_number + 1) == state.number_of_players:
            self.OMW = 0.0
            return

        round_num = 0
        for round in self.rounds:
            if round.games_won > state.players[round.opp_number].rounds[round_num].games_won:
                self.points += 3
            if round.games_won == 1 and state.players[round.opp_number].rounds[round_num].games_won == 1:
                self.points += 1
            round_num += 1

        # calculate OMW percentage
        omwp = 0
        round_list = []
        
        for round in self.rounds:
            opp_num = round.opp_number
            opp_player = state.players[opp_num]   
            opp_match_wins = 0
            opp_matches = 0            
            round_num = 0

            for opp_round in opp_player.rounds:                
                if state.bye_player and (opp_num + 1) == state.number_of_players:
                    continue # byes dont count
                else:
                    opp_matches += 1
                    if opp_round.games_won > state.players[opp_round.opp_number].rounds[round_num].games_won:
                        opp_match_wins += 1
                round_num += 1
            
            if opp_matches == 0:
                round_list.append(0)

            else:
                oppwp = float(float(opp_match_wins)/(float(opp_matches)))
                if oppwp < .33:
                    oppwp = .33
                round_list.append(oppwp)
        
        omwp = sum(round_list)/len(round_list)
        self.OMW = omwp


    def player_has_played_target(self, opp_num: int) -> bool:
        has_played = False
        for round in self.rounds:
            if round.opp_number == opp_num:
                has_played = True
                break
        return has_played


def get_final_results(state: State) -> str:
    form_string = f"""<!DOCTYPE html>
    <html>
    <body>
    <h2>FINAL RESULTS</h2>
        <br>"""

    pnum = len(state.ordered_pairing_list)
    start = 0
    while (start + 1) <= pnum:
        form_string += f"""Place {start + 1}: Player {state.ordered_pairing_list[start]}<br>    
        <br><br>"""
        start += 1
    form_string += """<br><br>
        </body>
        </html>"""
    return form_string   

def get_pairing_controls(state: State) -> str:
    form_string = f"""<!DOCTYPE html>
    <html>
    <body>
    <h2>Round {state.played_rounds + 1} : {state.state_string}</h2>
    <form action="http://localhost:7071/SwissPairings/{state.state_string}" method="POST">
        <br>"""

    pnum = len(state.ordered_pairing_list)
    start = 0
    while (start + 1) <= pnum:
        form_string += f"""Player {state.ordered_pairing_list[start]} vs Player {state.ordered_pairing_list[start + 1]}<br>
        <input type="radio" name="{state.ordered_pairing_list[start]}_{state.ordered_pairing_list[start+1]}" value="3_0">
        Player {state.ordered_pairing_list[start]}: 3-0&nbsp
        <input type="radio" name="{state.ordered_pairing_list[start]}_{state.ordered_pairing_list[start+1]}" value="2_1">
        Player {state.ordered_pairing_list[start]}: 2-1&nbsp
        <input type="radio" name="{state.ordered_pairing_list[start]}_{state.ordered_pairing_list[start+1]}" value="1_2">
        Player {state.ordered_pairing_list[start]}: 1-2&nbsp
        <input type="radio" name="{state.ordered_pairing_list[start]}_{state.ordered_pairing_list[start+1]}" value="0_3">
        Player {state.ordered_pairing_list[start]}: 0-3&nbsp
        <input type="radio" name="{state.ordered_pairing_list[start]}_{state.ordered_pairing_list[start+1]}" value="1_1">
        Player {state.ordered_pairing_list[start]}: 1-1&nbsp
        <br><br>"""
        start += 2
    form_string += """<br><br>
        <button type="submit">Submit</button>
        </form>
        </body>
        </html>"""
    return form_string           
    
def get_header(pnum: int, rnum: int, rcurr: int, bye_player: bool) -> list:

    pnum_header = [int(x) for x in '{:0{size}b}'.format(pnum,size=4)]
    rnum_header = [int(x) for x in '{:0{size}b}'.format(rnum,size=3)]
    rcurr_header = [int(x) for x in '{:0{size}b}'.format(rcurr,size=3)]
    bye_bit = [1] if bye_player else [0]
    bit_list = pnum_header + rnum_header + rcurr_header + bye_bit

    return bit_list

def pad_bits(header: list) -> list:
    length = len(header)            
    fill = length % 6
    if fill != 0:
        for _ in range(6 - fill):
            header.append(0)
    return header

def get_player_width(pnum: int) -> int:
    width = 1
    while (2**width < pnum):
        width += 1
    return width

def decode_header(ba_string: str):
    
    number_of_players = int(ba_string[:4], 2)
    number_of_rounds = int(ba_string[4:7] ,2)
    played_rounds = int(ba_string[7:10] ,2)
    bye_player = True if bool(int(ba_string[10:11])) else False
    return number_of_players, number_of_rounds, played_rounds, bye_player

def main(req: func.HttpRequest) -> func.HttpResponse:

    logging.info('Python HTTP trigger function processed a request.')

    state_string = req.route_params.get('state')

    if "GET" in req.method:
        if state_string is None:
            return func.HttpResponse(body=new_game_form, mimetype="text/html")
        else:
            current_state = State(state_string)

            if current_state.played_rounds < current_state.number_of_rounds:
                pairing_form = get_pairing_controls(current_state)
            else:
                pairing_form = get_final_results(current_state)

            return func.HttpResponse(body=pairing_form, mimetype="text/html")

    elif "POST" in req.method:
        if state_string is None:
            current_state = State(None)
            current_state.build_first_state_string(req.form)
            headers = {"Location":  f"http://localhost:7071/SwissPairings/{current_state.state_string}"}
            return func.HttpResponse(status_code=302, headers=headers)

        else:
            current_state = State(state_string)
            current_state.update_history(req.form)
            current_state.build_new_state_string()
            headers = {"Location":  f"http://localhost:7071/SwissPairings/{current_state.state_string}"}
            return func.HttpResponse(status_code=302, headers=headers)

    else:
        raise ValueError(f"Unexpected http method {req.method}")

