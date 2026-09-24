
# if __name__ == "__main__":
from flask import Flask, render_template, jsonify, url_for
import webbrowser
import argparse
from waitress import serve
from multiprocessing import Process, Queue
from DUTs.BMS import *
from Interfaces.USB_TO_SPI_BYTE import *
from DUTs.BMS_Configs.ADBMS6830 import *

app = Flask(__name__,  template_folder='./templates/TradeShow_Demos/Discharge_Algo_Demo', static_folder="static")

data_queue = Queue()
dcc_queue = Queue()




@app.route("/index", methods=['GET'])
def index():
    return render_template('discharge_algo.html')


@app.route("/data_update", methods=['GET'])
def data_update():
    data = []
    while not data_queue.empty():
        data.append(data_queue.get())
    return jsonify(data)

@app.route("/dcc_toggle/<dcc>/<int:state>", methods=['POST'])
def dcc_update(dcc, state):
    if state:
        dcc_queue.put({'DCC': 'DCC%s' % dcc, 'Val': True})
    else:
        dcc_queue.put({'DCC': 'DCC%s' % dcc, 'Val': False})
    return 'OK'

iir_table = [[0,0],[1,0.03125],[2,0.061523438],[3,0.09085083],[4,0.119261742],[5,0.146784812],[6,0.173447787],[7,0.199277543],[8,0.22430012],[9,0.248540741],[10,0.272023843],[11,0.294773098],[12,0.316811439],[13,0.338161081],[14,0.358843548],[15,0.378879687],[16,0.398289697],[17,0.417093144],[18,0.435308983],[19,0.452955577],[20,0.470050715],[21,0.48661163],[22,0.502655017],[23,0.518197048],[24,0.53325339],[25,0.547839222],[26,0.561969246],[27,0.575657707],[28,0.588918404],[29,0.601764703],[30,0.614209557],[31,0.626265508],[32,0.637944711],[33,0.649258939],[34,0.660219597],[35,0.670837734],[36,0.681124055],[37,0.691088928],[38,0.700742399],[39,0.710094199],[40,0.719153756],[41,0.727930201],[42,0.736432382],[43,0.74466887],[44,0.752647968],[45,0.760377719],[46,0.767865915],[47,0.775120105],[48,0.782147602],[49,0.788955489],[50,0.79555063],[51,0.801939673],[52,0.808129058],[53,0.814125025],[54,0.819933618],[55,0.825560693],[56,0.831011921],[57,0.836292799],[58,0.841408649],[59,0.846364628],[60,0.851165734],[61,0.855816805],[62,0.860322529],[63,0.86468745],[64,0.868915968],[65,0.873012344],[66,0.876980708],[67,0.880825061],[68,0.884549278],[69,0.888157113],[70,0.891652203],[71,0.895038072],[72,0.898318132],[73,0.90149569],[74,0.90457395],[75,0.907556014],[76,0.910444888],[77,0.913243486],[78,0.915954627],[79,0.918581045],[80,0.921125387],[81,0.923590219],[82,0.925978024],[83,0.928291211],[84,0.930532111],[85,0.932702982],[86,0.934806014],[87,0.936843326],[88,0.938816972],[89,0.940728942],[90,0.942581162],[91,0.944375501],[92,0.946113767],[93,0.947797711],[94,0.949429033],[95,0.951009376],[96,0.952540333],[97,0.954023447],[98,0.955460215],[99,0.956852083],[100,0.958200455],[101,0.959506691],[102,0.960772107],[103,0.961997979],[104,0.963185542],[105,0.964335994],[106,0.965450494],[107,0.966530166],[108,0.967576098],[109,0.968589345],[110,0.969570928],[111,0.970521837],[112,0.971443029],[113,0.972335435],[114,0.973199952],[115,0.974037454],[116,0.974848783],[117,0.975634759],[118,0.976396173],[119,0.977133792],[120,0.977848361],[121,0.9785406],[122,0.979211206],[123,0.979860856],[124,0.980490204],[125,0.981099885],[126,0.981690514],[127,0.982262685],[128,0.982816976],[129,0.983353946],[130,0.983874135],[131,0.984378068],[132,0.984866254],[133,0.985339183],[134,0.985797334],[135,0.986241167],[136,0.986671131],[137,0.987087658],[138,0.987491169],[139,0.98788207],[140,0.988260755],[141,0.988627606],[142,0.988982994],[143,0.989327275],[144,0.989660798],[145,0.989983898],[146,0.990296901],[147,0.990600123],[148,0.990893869],[149,0.991178436],[150,0.991454109],[151,0.991721169],[152,0.991979882],[153,0.992230511],[154,0.992473307],[155,0.992708516],[156,0.992936375],[157,0.993157114],[158,0.993370954],[159,0.993578111],[160,0.993778795],[161,0.993973208],[162,0.994161545],[163,0.994343997],[164,0.994520747],[165,0.994691974],[166,0.99485785],[167,0.995018542],[168,0.995174212],[169,0.995325018],[170,0.995471111],[171,0.995612639],[172,0.995749744],[173,0.995882565],[174,0.996011235],[175,0.996135883],[176,0.996256637],[177,0.996373617],[178,0.996486942],[179,0.996596725],[180,0.996703077],[181,0.996806106],[182,0.996905915],[183,0.997002605],[184,0.997096274],[185,0.997187015],[186,0.997274921],[187,0.99736008],[188,0.997442577],[189,0.997522497],[190,0.997599919],[191,0.997674921],[192,0.99774758],[193,0.997817968],[194,0.997886157],[195,0.997952214],[196,0.998016208],[197,0.998078201],[198,0.998138257],[199,0.998196437],[200,0.998252798],[201,0.998307398],[202,0.998360292],[203,0.998411533],[204,0.998461172],[205,0.998509261],[206,0.998555846],[207,0.998600976],[208,0.998644696],[209,0.998687049],[210,0.998728079],[211,0.998767826],[212,0.998806332],[213,0.998843634],[214,0.99887977],[215,0.998914777],[216,0.998948691],[217,0.998981544],[218,0.999013371],[219,0.999044203],[220,0.999074072],[221,0.999103007],[222,0.999131038],[223,0.999158193],[224,0.999184499],[225,0.999209984],[226,0.999234672],[227,0.999258588],[228,0.999281757],[229,0.999304203],[230,0.999325946],[231,0.99934701],[232,0.999367416],[233,0.999387185],[234,0.999406335],[235,0.999424887],[236,0.999442859],[237,0.99946027],[238,0.999477137],[239,0.999493476],[240,0.999509305],[241,0.999524639],[242,0.999539494],[243,0.999553885],[244,0.999567826],[245,0.999581331],[246,0.999594415],[247,0.999607089],[248,0.999619368],[249,0.999631263],[250,0.999642786],[251,0.999653949],[252,0.999664763],[253,0.999675239],[254,0.999685388],[255,0.999695219],[256,0.999704744],[257,0.99971397],[258,0.999722909],[259,0.999731568],[260,0.999739956],[261,0.999748083],[262,0.999755955],[263,0.999763582],[264,0.99977097],[265,0.999778127],[266,0.99978506],[267,0.999791777],[268,0.999798284],[269,0.999804588],[270,0.999810695],[271,0.99981661],[272,0.999822341],[273,0.999827893],[274,0.999833271],[275,0.999838482],[276,0.999843529],[277,0.999848419],[278,0.999853156],[279,0.999857745],[280,0.99986219],[281,0.999866497],[282,0.999870669],[283,0.99987471],[284,0.999878626],[285,0.999882419],[286,0.999886093],[287,0.999889653],[288,0.999893101],[289,0.999896441],[290,0.999899678],[291,0.999902813],[292,0.99990585],[293,0.999908792],[294,0.999911642],[295,0.999914403],[296,0.999917078],[297,0.99991967],[298,0.99992218],[299,0.999924612],[300,0.999926968],[301,0.99992925],[302,0.999931461],[303,0.999933603],[304,0.999935678],[305,0.999937688],[306,0.999939635],[307,0.999941521],[308,0.999943349],[309,0.999945119],[310,0.999946834],[311,0.999948496],[312,0.999950105],[313,0.999951664],[314,0.999953175],[315,0.999954638],[316,0.999956056],[317,0.999957429],[318,0.999958759],[319,0.999960048],[320,0.999961297],[321,0.999962506],[322,0.999963678],[323,0.999964813],[324,0.999965912],[325,0.999966978],[326,0.99996801],[327,0.999969009],[328,0.999969978],[329,0.999970916],[330,0.999971825],[331,0.999972705],[332,0.999973558],[333,0.999974385],[334,0.999975185],[335,0.999975961],[336,0.999976712],[337,0.99997744],[338,0.999978145],[339,0.999978828],[340,0.999979489],[341,0.99998013],[342,0.999980751],[343,0.999981353],[344,0.999981935],[345,0.9999825],[346,0.999983047],[347,0.999983577],[348,0.99998409],[349,0.999984587],[350,0.999985069],[351,0.999985535],[352,0.999985987],[353,0.999986425],[354,0.999986849],[355,0.99998726],[356,0.999987658],[357,0.999988044],[358,0.999988418],[359,0.99998878],[360,0.99998913],[361,0.99998947],[362,0.999989799],[363,0.999990118],[364,0.999990427],[365,0.999990726],[366,0.999991016],[367,0.999991296],[368,0.999991568],[369,0.999991832],[370,0.999992087],[371,0.999992334],[372,0.999992574],[373,0.999992806],[374,0.999993031],[375,0.999993249],[376,0.99999346],[377,0.999993664],[378,0.999993862],[379,0.999994054],[380,0.99999424],[381,0.99999442],[382,0.999994594],[383,0.999994763],[384,0.999994927],[385,0.999995085],[386,0.999995239],[387,0.999995388],[388,0.999995532],[389,0.999995671],[390,0.999995807],[391,0.999995938],[392,0.999996065],[393,0.999996188],[394,0.999996307],[395,0.999996422],[396,0.999996534],[397,0.999996642],[398,0.999996747],[399,0.999996849],[400,0.999996947],[401,0.999997043],[402,0.999997135],[403,0.999997225],[404,0.999997311],[405,0.999997395],[406,0.999997477],[407,0.999997556],[408,0.999997632],[409,0.999997706],[410,0.999997778],[411,0.999997847],[412,0.999997914],[413,0.99999798],[414,0.999998043],[415,0.999998104],[416,0.999998163],[417,0.999998221],[418,0.999998276],[419,0.99999833],[420,0.999998382],[421,0.999998433],[422,0.999998482],[423,0.999998529],[424,0.999998575],[425,0.99999862],[426,0.999998663],[427,0.999998705],[428,0.999998745],[429,0.999998784],[430,0.999998822],[431,0.999998859],[432,0.999998895],[433,0.999998929],[434,0.999998963],[435,0.999998995],[436,0.999999027],[437,0.999999057],[438,0.999999086],[439,0.999999115],[440,0.999999143],[441,0.999999169],[442,0.999999195],[443,0.999999221],[444,0.999999245],[445,0.999999269],[446,0.999999291],[447,0.999999314],[448,0.999999335],[449,0.999999356],[450,0.999999376],[451,0.999999395],[452,0.999999414],[453,0.999999433],[454,0.99999945],[455,0.999999467],[456,0.999999484],[457,0.9999995]]


def iir_scale(old_ct, new_ct, need_scale, offset):
    if not need_scale:
        return 1, False, 0
    # CT has wrapped around
    if new_ct < old_ct:
        ct = new_ct + 2048 - old_ct + offset
    else:
        ct = new_ct - old_ct + offset
    # print('CT: %s'%ct)
    if ct >= len(iir_table):
        return 1, False, 0
    else:
        return iir_table[ct][1], True, offset


def data_collection(queue, dcc_input):
    try:
        cal_in_progress = True
        cal_time = time.time()
        cal_period = 15
        cal = []
        cal_base = []
        cal_first_conv = False
        switches_disabled = True
        iir_scaling_required = False
        balance_accur = 0.005
        min_balance_val = 3.7
        cal_state = 'start'
        prev_ct = 0
        gain = [1]*16
        board_list = [{'Device': ADBMS6830}]
        init_list = [
            {'command': '$SPI_SET_FREQUENCY_kHz$', 'arguments': {'Frequency': 2000}},
            {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 400}},
            {'command': 'WRCFGA', 'arguments': {'FC': 5}},
            {'command': 'WRCFGB'},
            {'command': 'RDCFGA', 'map_key': 'CFG'},
            {'command': 'RDCFGB', 'map_key': 'CFG'},
            {'command': 'ADCV', 'arguments': {'CONT': True}},
            {'command': '$DELAY_MS$', 'arguments': {'Delay': 5}}
        ]
        balance_list = [
            {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
            {'command': 'WRCFGB'},
            {'command': 'SNAP'},
            {'command': 'RDSTATC', 'map_key': 'CT'},
            {'command': 'UNSNAP'},
        ]
        meas_list = [
            {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
            {'command': 'SNAP'},
            {'command': 'RDFCA', 'map_key': 'CELLS'},
            {'command': 'RDFCB', 'map_key': 'CELLS'},
            {'command': 'RDFCC', 'map_key': 'CELLS'},
            {'command': 'RDFCD', 'map_key': 'CELLS'},
            {'command': 'RDFCE', 'map_key': 'CELLS'},
            {'command': 'RDFCF', 'map_key': 'CELLS'},
            {'command': 'RDSTATC', 'map_key': 'CT'},
            {'command': 'UNSNAP'},
        ]
        redundant_meas_list = [
            {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
            {'command': 'MUTE'},
            {'command': 'SNAP'},
            # {'command': 'ADSV', 'arguments': {'CONT': True}},
            {'command': 'RDSTATC', 'map_key': 'MUTE'},
            {'command': 'UNSNAP'},
            {'command': '$DELAY_MS$', 'arguments': {'Delay': 16}},
            {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
            {'command': 'UNMUTE'},
            {'command': 'SNAP'},
            # {'command': 'ADSV', 'arguments': {'CONT': False}},
            {'command': 'RDACA', 'map_key': 'CELLS'},
            {'command': 'RDACB', 'map_key': 'CELLS'},
            {'command': 'RDACC', 'map_key': 'CELLS'},
            {'command': 'RDACD', 'map_key': 'CELLS'},
            {'command': 'RDACE', 'map_key': 'CELLS'},
            {'command': 'RDACF', 'map_key': 'CELLS'},
            {'command': 'RDSTATC', 'map_key': 'UNMUTE'},
            {'command': 'UNSNAP'},
        ]
        switch_config = {
            'DCC1': False, 'DCC2': False, 'DCC3': False, 'DCC4': False, 'DCC5': False, 'DCC6': False, 'DCC7': False,
            'DCC8': False, 'DCC9': False, 'DCC10': False, 'DCC11': False, 'DCC12': False, 'DCC13': False,
            'DCC14': False, 'DCC15': False, 'DCC16': False}
        switch_config_base = {
            'DCC1': False, 'DCC2': False, 'DCC3': False, 'DCC4': False, 'DCC5': False, 'DCC6': False, 'DCC7': False,
            'DCC8': False, 'DCC9': False, 'DCC10': False, 'DCC11': False, 'DCC12': False, 'DCC13': False,
            'DCC14': False, 'DCC15': False, 'DCC16': False}
        acells = []
        fcells = []
        rawcells = []
        offset = 0
        interface = USB_TO_SPI_BYTE('COM', 115200)
        bms = BMS(interface)
        results = bms.run_generic_command_list(init_list, board_list)
        # print(results['CFG'][0])

        results = bms.run_generic_command_list(redundant_meas_list, board_list)
        for i, cell in enumerate(ADBMS6830.AVERAGED_CELLS):
            acells.append(results['CELLS'][0][cell])
            fcells.append(results['CELLS'][0][cell])
        prev_ct = results['UNMUTE'][0]['CT']
        redundant_timer = 0

        while True:
            while not dcc_input.empty():
                config = dcc_input.get()
                print(config)
                switch_config[config['DCC']] = config['Val']
            packet = {
                'FCELLS': [],
                'RAWCELLS': [],
                'ACELLS': [],
                'CT': None
            }
            redundant_timer -= 1
            if redundant_timer <= 0:
                if not cal_in_progress:
                    redundant_timer = 100
                    results = bms.run_generic_command_list(redundant_meas_list, board_list)
                    acells = []
                    for i, cell in enumerate(ADBMS6830.AVERAGED_CELLS):
                        acells.append(results['CELLS'][0][cell])
                    mute_ct = results['MUTE'][0]['CT']
                    unmute_ct = results['UNMUTE'][0]['CT']
                    if unmute_ct < mute_ct:
                        unmute_ct += 2048
                    offset = unmute_ct - mute_ct
                    if not iir_scaling_required:
                        iir_scaling_required = True
                        prev_ct = results['MUTE'][0]['CT']
            results = bms.run_generic_command_list(meas_list, board_list)
            current_ct = results['CT'][0]['CT']
            scale, iir_scaling_required, offset = iir_scale(prev_ct, current_ct, iir_scaling_required, offset)
            rawcells = []
            if not cal_in_progress:
                fcells = []
            for i, cell in enumerate(ADBMS6830.FILTERED_CELLS):
                packet['ACELLS'].append(acells[i])
                if not cal_in_progress:
                    packet['RAWCELLS'].append(results['CELLS'][0][cell])
                    fcells.append(results['CELLS'][0][cell])
                else:
                    packet['RAWCELLS'].append(fcells[i])
                rawcells.append(results['CELLS'][0][cell])
                if switches_disabled:
                    packet['FCELLS'].append(results['CELLS'][0][cell] * (1 + (gain[i] - 1) * (1 - scale)))
                else:
                    packet['FCELLS'].append(results['CELLS'][0][cell] * (1 + (gain[i] - 1) * (scale)))
            packet['CT'] = results['CT'][0]['CT']
            if time.time() - cal_time > cal_period or cal_in_progress:
                if not cal_state:
                    cal_state = 'start'
                if cal_state == 'start':
                    print("Starting CAl")
                    # Turn off discharge switches, start timer for len of IIR filter
                    board_list[0].update(switch_config_base)
                    dat = bms.run_generic_command_list(balance_list, board_list)
                    prev_ct = dat['CT'][0]['CT']
                    iir_scaling_required = True
                    cal_state = 'switch_off'
                    switches_disabled = True
                    cal_in_progress = True
                    print("CAL - Switch Off")
                elif cal_state == 'switch_off':
                    # Check CT for iir settle, record base measurement, turn on evens
                    ct = 0
                    if current_ct < prev_ct:
                        ct = current_ct + 2048 - prev_ct
                    else:
                        ct = current_ct - prev_ct
                    if ct >= iir_table[-1][0]:
                        cal_state = 'switch_on'
                        switches_disabled = False
                        cal_in_progress = True
                        # cal_base = packet['RAWCELLS']  # Record base
                        cal_base = rawcells  # Record base
                        # Determine DCC bits
                        min_cell = min(cal_base)
                        # Determine Balance Switches
                        # switch_config.update(switch_config_base)
                        # for i, cell in enumerate(cal_base):
                        #     if (cell > (min_cell + balance_accur)) and cell > min_balance_val:
                        #         switch_config['DCC%s' % str(i + 1)] = True
                        # Write switches
                        board_list[0].update(switch_config)
                        # print(board_list[0])
                        dat = bms.run_generic_command_list(balance_list, board_list)
                        prev_ct = dat['CT'][0]['CT']
                        iir_scaling_required = True
                        cal_first_conv = True
                        print("CAL - Switch On")
                elif cal_state == 'switch_on':
                    # Check CT for iir settle, dynamically update gain
                    ct = 0
                    if current_ct < prev_ct:
                        ct = current_ct + 2048 - prev_ct
                    else:
                        ct = current_ct - prev_ct
                    if ct >= iir_table[-1][0]:
                        cal_state = None
                        # cal = packet['RAWCELLS']  # Record switch active
                        cal = rawcells  # Record switch active
                        cal_in_progress = False
                        gain = []
                        for i, cell in enumerate(ADBMS6830.FILTERED_CELLS):
                            gain.append(cal_base[i] / cal[i])
                        cal_time = time.time()
                        print("CAL - Done")
                    else:
                        # cal = packet['RAWCELLS']
                        cal = rawcells
                        scale = iir_table[ct][1]
                        gain = []
                        for i, cell in enumerate(ADBMS6830.FILTERED_CELLS):
                            gain.append((cal_base[i] - cal[i] + cal[i] * scale) / (cal[i] * scale))
                        if cal_first_conv:
                            cal_first_conv = False
                            packet['FCELLS'] = []
                            for i, cell in enumerate(ADBMS6830.FILTERED_CELLS):
                                packet['FCELLS'].append(results['CELLS'][0][cell] * (1 + (gain[i] - 1) * (scale)))
            queue.put(packet)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    # data_collection(data_queue)
    background_process = Process(target=data_collection, args=(data_queue, dcc_queue))
    background_process.start()

    webbrowser.open('http://127.0.0.1:5000/index')
    serve(app, host='127.0.0.1', port='5000', threads=6)
