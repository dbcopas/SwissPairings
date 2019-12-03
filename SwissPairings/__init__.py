import logging
import random
import bitarray
import binascii
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
                '+' : bitarray.bitarray('111100'),
                '!' : bitarray.bitarray('111101'),
                '#' : bitarray.bitarray('111110'),
                '@' : bitarray.bitarray('111111'),
            }

class Players:
    def __init__(self, pnum: int):
         

def get_pairing_controls(player_num_ary: list, state: str, current_round: int) -> str:
    form_string = f"""<!DOCTYPE html>
    <html>
    <body>
    <h2>Round {current_round + 1} : {state}</h2>
    <form action="http://localhost:7071/SwissPairings/{state}" method="POST">
        <br>"""

    pnum = len(player_num_ary)
    start = 0
    while (start + 1) <= pnum:
        form_string += f"""Player {player_num_ary[start]} vs Player {player_num_ary[start + 1]}<br>
        <input type="radio" name="{player_num_ary[start]}_{player_num_ary[start+1]}" value="win">
        {player_num_ary[start]} Win&nbsp
        <input type="radio" name="{player_num_ary[start]}_{player_num_ary[start+1]}" value="loss">
        {player_num_ary[start]} Loss&nbsp
        <input type="radio" name="{player_num_ary[start]}_{player_num_ary[start+1]}" value="tie">
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
    rcurr_header = [int(x) for x in '{:0{size}b}'.format(0,size=3)]
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

def main(req: func.HttpRequest) -> func.HttpResponse:

    logging.info('Python HTTP trigger function processed a request.')

    state = req.route_params.get('state')

    if "GET" in req.method:
        if state is None:
            return func.HttpResponse(body=new_game_form, mimetype="text/html")
        else:
            ba = bitarray.bitarray()
            ba.encode(symbols, state)
            ba_string = ba.to01()
            number_of_players = int(ba_string[:4], 2)
            number_of_rounds = int(ba_string[4:7] ,2)
            current_round = int(ba_string[7:10] ,2)

            if current_round == 0:
                width = get_player_width(number_of_players)
                start_index = 10
                end_index = start_index + width
                ordered_pairing_list = []
                for i in range(number_of_players):
                    player_string = ba_string[start_index:end_index]
                    ordered_pairing_list.append(int(player_string, 2))
                    start_index = end_index
                    end_index = start_index + width
                pairing_form = get_pairing_controls(ordered_pairing_list, state, current_round)                
            else:

                #read history
                #calculate rankings
                #build the ordered list that represents the pairings
                #get the control

                pass
            return func.HttpResponse(body=pairing_form, mimetype="text/html")

    elif "POST" in req.method:
        if state is None:

            # randomize the players
            # encode the player order in a state that has
            # 4 bits for pnum
            # 3 bits for rounds
            # 3 bits for current round
            # var bits based on pnum, sequence of pairings
            # redirect to GET with that state (and have the get with state see this and render controls)

            pnum = int(req.form['pnum'])
            rnum = int(req.form['rnum'])

            if pnum % 2 == 1:
                pnum = pnum + 1

            header = get_header(pnum, rnum, 0)  

            players = []
            for i in range(pnum):
                players.append(i)    
            random.shuffle(players)
            width = get_player_width(pnum)

            for player in players:
                seq_header = [int(x) for x in '{:0{size}b}'.format(player,size=width)]
                header = header + seq_header

            header = pad_bits(header)
            ba = bitarray.bitarray(header)
            state = ba.decode(symbols)
            state_string = ''.join(state)
            headers = {"Location":  f"http://localhost:7071/SwissPairings/{state_string}"}
            return func.HttpResponse(status_code=302, headers=headers)

        else:

            # decode the state in to 
            # 4 bits for pnum
            # 3 bits for rounds
            # 3 bits for current round
            # var bits based on pnum, sequential 0-n list of results from previous rounds
            #  where the first bits are the opponent and the next 2 are the results 00 loss 01 win 1x tie

            # this also happens on get for result controls

            # parse the form values for the results from that round
            # calculate the rankings 

            return func.HttpResponse("expect the results of a round")
    else:
        raise ValueError(f"Unexpected http method {req.method}")


    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello {name}!")
    else:
        return func.HttpResponse(
             "Please pass a name on the query string or in the request body",
             status_code=400
        )
