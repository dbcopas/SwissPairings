import logging
import random
import bitarray
from enum import Enum
import azure.functions as func

#base_url = "http://localhost:7071"
base_url = "https://swisspairings.azurewebsites.net"

PLAYER_NUMBER_BITS = 7 # because 129 players is 1 player too many :')
ROUND_NUMBER_BITS = 4 # because 17 rounds would be inhumane. 16 is totally cool though


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

    def __init__(self, state_string: str, http_method: str):

        self.number_of_players = 0
        self.played_rounds = 0
        self.number_of_rounds = 0
        self.state_string = ""
        self.ordered_pairing_list = []
        self.players = []
        self.bye_player = False
        self.ranked_player_list = []

        # consume the state if it is there to be consumed
        if state_string is not None:

            ba = bitarray.bitarray()

            ba.encode(symbols, state_string.split("_")[0])
            ba_string = ba.to01()
            self.number_of_players, self.number_of_rounds, self.played_rounds, self.bye_player = decode_header(ba_string) 
            self.state_string = state_string

            for i in range(self.number_of_players):
                player = Player(i)
                self.players.append(player)

            if self.played_rounds > 0:

                # read the history from the state in to the player objs, calc points and get rankings
                self.populate_player_object_with_from_history_in_state(ba_string)

                if "POST" in http_method:
                    return # we won't need to do the rest

                ranked_player_list = self.get_player_rankings()
                self.ranked_player_list = ranked_player_list

                # if game isn't over yet, create the next pairings from the rankings (this is complicated)
                if self.played_rounds < self.number_of_rounds:
                    self.create_pairings_from_ranklist(ranked_player_list)

                # the rankings are final now                
                else:
                    for player in ranked_player_list:
                        self.ordered_pairing_list.append(player.player_number)
        
            # if this is the first round, read the state (made in the post) into the pairing list for the view to consume
            if self.played_rounds == 0 and "GET" in http_method: 
                width = get_player_width(self.number_of_players)
                start_index = PLAYER_NUMBER_BITS + ROUND_NUMBER_BITS + ROUND_NUMBER_BITS + 1
                end_index = start_index + width
                for i in range(self.number_of_players):
                    player_string = ba_string[start_index:end_index]
                    self.ordered_pairing_list.append(int(player_string, 2))
                    start_index = end_index
                    end_index = start_index + width

    # this is the only hard part of the app -> 
    # see https://www.channelfireball.com/all-strategy/articles/understanding-standings-part-i-tournament-structure-the-basics/
    def create_pairings_from_ranklist(self, ranked_player_list: list):
        self.ordered_pairing_list = []                    
        next_target = 1
        for player in ranked_player_list:
            player_matched = False

            # some other player put this player in the list because they paired with them
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

                    # start looking again from the top
                    next_target = 1

                # some other player put this player in the list because they paired with them
                # also don't try to match with ourself (in case there was a swap and we look through the list again)
                if ranked_player_list[next_target].player_number in self.ordered_pairing_list \
                    or ranked_player_list[next_target].player_number == player.player_number:
                    next_target += 1
                    continue

                # if our target hasn't played us, this is our pair
                if not player.player_has_played_target(ranked_player_list[next_target].player_number):
                    self.ordered_pairing_list.append(player.player_number)
                    self.ordered_pairing_list.append(ranked_player_list[next_target].player_number)
                    next_target = 1
                    player_matched = True
                else:
                    next_target += 1


    # read the history from the state in to the player objs, calc points and get rankings
    def populate_player_object_with_from_history_in_state(self, ba_string: str):
        width = get_player_width(self.number_of_players)
        start_index = PLAYER_NUMBER_BITS + ROUND_NUMBER_BITS + ROUND_NUMBER_BITS + 1
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
        

    # may need to add 2nd and 3rd tie breakers here
    def get_player_rankings(self) -> list:
        return sorted(self.players, key = lambda x: (x.points, x.OMW), reverse=True)

    # create the random pairings (called from the post of game setup)
    def build_first_state_string(self, form: dict):

        number_of_players = int(form['pnum']) # 1 indexed
        number_of_rounds = int(form['rnum']) # 1 indexed

        if number_of_players % 2 == 1:
            number_of_players += 1
            self.bye_player = True

        header = get_header(number_of_players, number_of_rounds, 0, self.bye_player)  

        player_numbers = []
        for i in range(number_of_players):
            player_numbers.append(i)    
        random.shuffle(player_numbers)
        width = get_player_width(number_of_players)

        for player_number in player_numbers:
            seq_header = [int(x) for x in '{:0{size}b}'.format(player_number,size=width)]
            header = header + seq_header

        header = pad_bits(header)
        ba = bitarray.bitarray(header)
        state = ba.decode(symbols)
        self.state_string = ''.join(state)

    # read results from result form post into the player objects (called from the post of results)
    def update_history(self, form: dict):

        for k, v in form.items():
            player_nums = k.split("_")
            player_1_num = int(player_nums[0])-1
            player_2_num = int(player_nums[1])-1
            player1 = self.players[player_1_num]
            player2 = self.players[player_2_num]
            games_won_nums = v.split("_")
            player1.add_result(player_2_num, int(games_won_nums[0]))
            player2.add_result(player_1_num, int(games_won_nums[1]))

    # encode the results into the state string (called from the post of results)
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
        old_state_string = self.state_string
        self.state_string = ''.join(state) + "_" + old_state_string
    
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
        
        # for this player, each round they play has an opponent with a OMW
        for round in self.rounds:
            opp_num = round.opp_number
            opp_player = state.players[opp_num]   
            opp_match_wins = 0
            opp_matches = 0            
            round_num = 0

            if state.bye_player and (opp_num + 1) == state.number_of_players:
                continue # byes dont count

            # our opponent for each round had rounds of their own
            for opp_round in opp_player.rounds:               
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
        
        if len(round_list) > 0:
            omwp = sum(round_list)/len(round_list)
            self.OMW = omwp
        else:
            self.OMW = 0

    def player_has_played_target(self, opp_num: int) -> bool:
        has_played = False
        for round in self.rounds:
            if round.opp_number == opp_num:
                has_played = True
                break
        return has_played

def get_new_game_form() -> str:
    new_game_form = f"""<!DOCTYPE html>
    <html>
    <body>
    <h1>Welcome to SwissPairings</h1>
    <h3>by Douglas Copas</h3>
    <h2>New Game</h2>
    <form action="{base_url}/SwissPairings" method="POST">
        Number of Players (Max 128)<br>
        <input type="text" name="pnum" value="8" required>
        <br><br>
        Number of Rounds (Max 16)<br>
        <input type="text" name="rnum" value = "3" required>
        <br>
        <br><br>
        <button type="submit">Submit</button>
        <br><br><br><br>
    </form>
    </body>
    <h3>Usage:</h3>
    <p>Enter the number of players. The suggested number of rounds is calculated automatically.<br>
    In a Swiss tournement this is log<sub>2</sub>(number of players). Assign each player a number.<br>
    Click Submit</p>
    </html>"""
    return new_game_form

def get_final_results(state: State) -> str:
    form_string = f"""<!DOCTYPE html>
    <head><style type="text/css">.centerText{{text-align: center;}}</style></head>
    <html>
    <body>"""
    form_string += get_rankings_and_links(state)
    form_string += "</body></html>"
    return form_string   

def get_pairing_controls(state: State) -> str:
    form_string = f"""<!DOCTYPE html>
    <head><style type="text/css">.centerText{{text-align: center;}}</style></head>
    <html>
    <body>
    <h2>Round {state.played_rounds + 1} : {state.state_string}</h2>
    <form action="{base_url}/SwissPairings/{state.state_string}" method="POST">
        <br>"""

    pnum = len(state.ordered_pairing_list)
    index = 0
    while (index) < pnum:
        is_bye_player = state.bye_player and (state.ordered_pairing_list[index] == pnum - 1 or state.ordered_pairing_list[index+1] == pnum - 1)
        current_players = [state.ordered_pairing_list[index]+1, state.ordered_pairing_list[index+1]+1]
        current_players.sort()
        first_player_string = current_players[0]
        second_player_string = current_players[1]
        if not is_bye_player:     
            form_string += f"""Player {first_player_string} vs Player {second_player_string}<br>
            <input type="radio" name="{first_player_string}_{second_player_string}" value="2_0">
            Player {first_player_string}: 2-0&nbsp
            <input type="radio" name="{first_player_string}_{second_player_string}" value="1_0">
            Player {first_player_string}: 1-0&nbsp
            <input type="radio" name="{first_player_string}_{second_player_string}" value="2_1">
            Player {first_player_string}: 2-1&nbsp
            <input type="radio" name="{first_player_string}_{second_player_string}" value="1_2">
            Player {first_player_string}: 1-2&nbsp
            <input type="radio" name="{first_player_string}_{second_player_string}" value="0_1">
            Player {first_player_string}: 0-1&nbsp
            <input type="radio" name="{first_player_string}_{second_player_string}" value="0_2">
            Player {first_player_string}: 0-2&nbsp
            <input type="radio" name="{first_player_string}_{second_player_string}" value="1_1">
            Player {first_player_string}: 1-1&nbsp
            <br><br>"""
        else:
            first_player_gets_bye = True if state.ordered_pairing_list[index+1] == pnum - 1 else False
            bye_player = state.ordered_pairing_list[index]+1 if first_player_gets_bye else state.ordered_pairing_list[index+1]+1
            bye_value = "2_0" if first_player_gets_bye else "0_2"
            form_string += f"""Player {bye_player} BYE<input type="hidden" name="{state.ordered_pairing_list[index]+1}_{state.ordered_pairing_list[index+1]+1}" value="{bye_value}"><br><br>"""
        index += 2

    form_string += """<br><br>
        <button type="submit">Submit</button>
        </form><br>"""

    if state.played_rounds > 0:
        form_string += get_rankings_and_links(state)

    form_string += f"""<br><a href="{base_url}/SwissPairings/">New game</a>"""

        

    form_string += """</body>
        </html>"""
    return form_string           
    
def get_rankings_and_links(state: State) -> str:
    form_string = """<h3>Rankings</h3><table style="width:25%"><tr><th>Rank</th><th>Player</th><th>Points</th><th>OMW%</th></tr>"""
    index = 0
    pnum = len(state.ordered_pairing_list)
    while (index) < pnum:
        form_string += f"""<tr><td class="centerText">{index + 1}</td><td class="centerText">{state.ranked_player_list[index].player_number + 1}</td>
        <td class="centerText">{state.ranked_player_list[index].points}</td><td class="centerText">{"{:.3f}".format(state.ranked_player_list[index].OMW)}</td></tr>"""
        index += 1
    form_string += "</table><br><br><h3>Past Rounds</h3>"

    states = state.state_string.split('_')
    states.reverse()

    link_list = []

    index = 0
    while (index) < state.played_rounds:
        part_index = 0
        state_url = ""
        while part_index <= index:
            state_url = states[part_index] + "_" + state_url
            part_index += 1
        form_string += f"""<a href="{base_url}/SwissPairings/{state_url[:-1]}">Revert to round {index + 1} result input</a><br><br>"""
        index += 1

    return form_string

def get_header(number_of_players: int, number_of_rounds: int, rounds_played: int, bye_player: bool) -> list:

    number_of_players -= 1 # 0 index the number of players

    number_of_players_header = [int(x) for x in '{:0{size}b}'.format(number_of_players,size=PLAYER_NUMBER_BITS)]
    number_of_rounds_header = [int(x) for x in '{:0{size}b}'.format(number_of_rounds,size=ROUND_NUMBER_BITS)]
    rounds_played_header = [int(x) for x in '{:0{size}b}'.format(rounds_played,size=ROUND_NUMBER_BITS)]
    bye_bit = [1] if bye_player else [0]
    bit_list = number_of_players_header + number_of_rounds_header + rounds_played_header + bye_bit

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
    
    number_of_players = int(ba_string[:PLAYER_NUMBER_BITS], 2) + 1 # 0 indexed
    number_of_rounds = int(ba_string[PLAYER_NUMBER_BITS:PLAYER_NUMBER_BITS+ROUND_NUMBER_BITS] ,2)
    played_rounds = int(ba_string[PLAYER_NUMBER_BITS+ROUND_NUMBER_BITS:PLAYER_NUMBER_BITS+ROUND_NUMBER_BITS+ROUND_NUMBER_BITS] ,2)
    bye_player = True if bool(int(ba_string[PLAYER_NUMBER_BITS+ROUND_NUMBER_BITS+ROUND_NUMBER_BITS:PLAYER_NUMBER_BITS+ROUND_NUMBER_BITS+ROUND_NUMBER_BITS+1])) else False
    return number_of_players, number_of_rounds, played_rounds, bye_player

def main(req: func.HttpRequest) -> func.HttpResponse:

    logging.info('Python HTTP trigger function processed a request.')

    state_string = req.route_params.get('state')

    if "GET" in req.method:
        if state_string is None:
            return func.HttpResponse(body=get_new_game_form(), mimetype="text/html")
        else:
            current_state = State(state_string, req.method)

            if current_state.played_rounds < current_state.number_of_rounds:
                pairing_form = get_pairing_controls(current_state)
            else:
                pairing_form = get_final_results(current_state)

            return func.HttpResponse(body=pairing_form, mimetype="text/html")

    elif "POST" in req.method:
        if state_string is None:
            current_state = State(None, req.method)
            current_state.build_first_state_string(req.form)
            headers = {"Location":  f"{base_url}/SwissPairings/{current_state.state_string}"}
            return func.HttpResponse(status_code=302, headers=headers)

        else:
            current_state = State(state_string, req.method)
            current_state.update_history(req.form)
            current_state.build_new_state_string()
            headers = {"Location":  f"{base_url}/SwissPairings/{current_state.state_string}"}
            return func.HttpResponse(status_code=302, headers=headers)

    else:
        raise ValueError(f"Unexpected http method {req.method}")

