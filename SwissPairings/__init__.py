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

    def __init__(self, state_string: str):

        self.number_of_players = 0
        self.played_rounds = 0
        self.number_of_rounds = 0
        self.state_string = ""
        self.ordered_pairing_list = []
        self.players = []

        if state_string is not None:
            ba = bitarray.bitarray()
            ba.encode(symbols, state_string)
            ba_string = ba.to01()
            self.number_of_players, self.number_of_rounds, self.played_rounds = decode_header(ba_string) 
            self.state_string = state_string
            for i in range(self.number_of_players):
                player = Player(i)
                self.players.append(player)   
            if self.played_rounds > 0:
                pass
                # build history
                # calculate rankings in the form of the ordered pairing list

        if self.played_rounds == 0: # create the ordered pairing list for the first round
            width = get_player_width(self.number_of_players)
            start_index = 10
            end_index = start_index + width
            for i in range(self.number_of_players):
                player_string = ba_string[start_index:end_index]
                self.ordered_pairing_list.append(int(player_string, 2))
                start_index = end_index
                end_index = start_index + width


    def build_first_state_string(self, form: dict):

        pnum = int(form['pnum'])
        rnum = int(form['rnum'])

        if pnum % 2 == 1:
            pnum = pnum + 1

        header = get_header(pnum, rnum, 0)  

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
        header = get_header(self.number_of_players, self.number_of_rounds, self.played_rounds)
        width = get_player_width(self.number_of_players)

        for round_number in range(self.played_rounds):
            for player in self.players:
                opp_number_string = [int(x) for x in '{:0{size}b}'.format(player.rounds[round_number].opp_number,size=width)]
                header = header + opp_number_string
                if player.rounds[round_number].result == Result.WIN:
                    result_bits = [0,1]
                elif player.rounds[round_number].result == Result.LOSS:
                    result_bits = [0,0]
                else:
                    result_bits = [1,1]
                header = header + result_bits

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
            player1_result = Result[v]
            player1.add_result(player_2_num, player1_result)
            if v == "TIE":
                player2_result = Result.TIE
            else:
                player2_result = Result.LOSS if v == "WIN" else Result.WIN
            player2.add_result(player_1_num, player2_result)
    
class Result(Enum):
    WIN = 1
    LOSS = 2
    TIE = 3

class Round:
    opp_number = -1
    result = -1
    def __init__(self, opp_number: int, result: Result):
        self.opp_number = opp_number
        self.result = result

class Player:
    player_number = -1
    rounds = []

    def __init__(self, pnum:int):
        self.rounds = []
        self.player_number = pnum

    def add_result(self, opp_number:int, result: Result):
        round = Round(opp_number, result)
        self.rounds.append(round)

def get_final_results(state: State) -> str:
    # just list the state and consume the ordered pairing list as the rank list
    return "you win"

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
        <input type="radio" name="{state.ordered_pairing_list[start]}_{state.ordered_pairing_list[start+1]}" value="WIN">
        {state.ordered_pairing_list[start]} Win&nbsp
        <input type="radio" name="{state.ordered_pairing_list[start]}_{state.ordered_pairing_list[start+1]}" value="LOSS">
        {state.ordered_pairing_list[start]} Loss&nbsp
        <input type="radio" name="{state.ordered_pairing_list[start]}_{state.ordered_pairing_list[start+1]}" value="TIE">
        Tie<br><br>"""
        start = start + 2
    form_string += """<br><br>
        <button type="submit">Submit</button>
        </form>
        </body>
        </html>"""
    return form_string           
    
def get_header(pnum: int, rnum: int, rcurr: int) -> list:

    pnum_header = [int(x) for x in '{:0{size}b}'.format(pnum,size=4)]
    rnum_header = [int(x) for x in '{:0{size}b}'.format(rnum,size=3)]
    rcurr_header = [int(x) for x in '{:0{size}b}'.format(rcurr,size=3)]
    bit_list = pnum_header + rnum_header + rcurr_header

    return bit_list

def pad_bits(header: list) -> list:
    length = len(header)            
    fill = length % 6
    if fill != 0:
        for i in range(6 - fill):
            header.append(0)
    return header

def get_player_width(pnum: int) -> int:
    width = 1
    while (2**width < pnum):
        width = width + 1
    return width

def decode_header(ba_string: str):
    
    number_of_players = int(ba_string[:4], 2)
    number_of_rounds = int(ba_string[4:7] ,2)
    played_rounds = int(ba_string[7:10] ,2)
    return number_of_players, number_of_rounds, played_rounds

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

