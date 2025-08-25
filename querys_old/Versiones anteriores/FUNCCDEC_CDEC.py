# -*- coding: utf-8 -*-
"""
Created on Tue Jul  6 15:01:03 2021

@author: felipe.ruiz
@editor: jose.rosales

"""

from scipy.interpolate import interp1d
import numpy as np


    
"""
Funciones de cota de Angostura

"""

def vol_angostura(cota):
    vol_angostura=0
    
    if cota <280:
        vol_angostura = 1.42084270641058E-02 * cota ** 2 - 7.55794967587359 * cota + 1005.0989369465
    elif cota <290:
        vol_angostura = 0.023812857004521 * cota ** 2 - 12.9330770375678 * cota + 1757.21857766058
    elif cota <296:
        vol_angostura = 5.76911113283868E-02 * cota ** 2 - 32.3727074657782 * cota + 4545.81085866535   
    elif cota <302:
        vol_angostura = 0.107207786948566 * cota ** 2 - 61.5307295123461 * cota + 8838.26697394881
    elif cota <310:
        vol_angostura = 0.141958163277288 * cota ** 2 - 82.4673316143121 * cota + 11991.7130189995
    elif cota <316:
        vol_angostura = 0.112940353957764 * cota ** 2 - 64.5547375536446 * cota + 9227.31750858668
    else:
        vol_angostura = 0.172040377016484 * cota ** 2 - 102.168372622437 * cota + 15211.766064903
        
    return vol_angostura


def cot_angostura(Volumen):
    Cot_ANGOSTURA=0
    
    if Volumen < 0.27:
        Cot_ANGOSTURA = -48.4192665413133 * Volumen ** 2 + 29.5296605308872 * Volumen + 265.545840411463
    elif Volumen <  2.07:
        Cot_ANGOSTURA = -1.55585853866169 * Volumen ** 2 + 7.54048794244096 * Volumen + 268.431509764293
    elif Volumen < 4.88:
        Cot_ANGOSTURA = -0.184330182119195 * Volumen ** 2 + 3.37699284229226 * Volumen + 271.791610100975
    elif Volumen < 9.55:
        Cot_ANGOSTURA = -0.112192998077952 * Volumen ** 2 + 2.8581581455128 * Volumen + 272.728365457533
    elif Volumen < 18.29:
        Cot_ANGOSTURA = -2.53694952744581E-02 * Volumen ** 2 + 1.37651004368551 * Volumen + 279.169734659089
    elif Volumen < 33.73:
        Cot_ANGOSTURA = -8.42735262859683E-03 * Volumen ** 2 + 0.810786824299806 * Volumen + 283.990615589921
    elif Volumen < 68.92:
        Cot_ANGOSTURA = -2.05377126600161E-03 * Volumen ** 2 + 0.431707705240237 * Volumen + 289.774750779038
    elif Volumen < 105.82:
        Cot_ANGOSTURA = -5.41145244634336E-04 * Volumen ** 2 + 0.256320173086788 * Volumen + 294.905402099063
    else:
        Cot_ANGOSTURA = -4.80482772640695E-04 * Volumen ** 2 + 0.253576434458394 * Volumen + 294.546288065969
        
    return Cot_ANGOSTURA


"""
Funciones de cota de Canutillar

"""

def vol_canutillar(cota):
    vol_canutillar=0
    
    if cota <230:
        vol_canutillar = 44.9739 * cota - 9894.258
    elif cota <240:
        vol_canutillar = 46.3472 * cota - 10210.117
    else:
        vol_canutillar = 50.7225 * cota - 11260.189
        
    return vol_canutillar


def cot_canutillar(Volumen):
    Cot_CANUTILLAR=0
    
    if Volumen < 449.739:
        Cot_CANUTILLAR = 0.022235119 * Volumen + 220.0
    elif Volumen <  913.211:
        Cot_CANUTILLAR = 0.021576276 * Volumen + 220.29631
    else:
        Cot_CANUTILLAR = 0.019715117 * Volumen + 221.99594
        
    return Cot_CANUTILLAR


"""
Funciones de cota de Colbun

"""

def vol_colbun(Cota):
    vol_COLBUN=0.0
    
    if Cota <393:
        vol_COLBUN = 319.1
    elif Cota <397:
        x=[393,394,395,396,397]
        y=[319.1,333.76,348.83,364.32,380.22]      
        volumen = interp1d(x,y)
        vol_COLBUN=volumen(Cota)
    else:
        a3 = 215.679132
        a2 = -564.993651
        a1 = 496.907289
        a0 = -146.591083
        CMAX = 437
        VMAX = 1550.63
        vol_COLBUN = (a1 * (Cota / CMAX) + a2 * (Cota / CMAX) * (Cota / CMAX) + a3 * (Cota / CMAX) * (Cota / CMAX) * (Cota / CMAX)  + a0) * VMAX
        
    return vol_COLBUN

def CotEST_COLBUN(Volumen):
    a0 = 364.83334314
    a1 = 0.1113822656
    a2 = -0.00008523
    a3 = 0.000000044
    a4 = -1.3231988*(10**(-11))
    a5 = 1.8734156*(10**(-15))
    Cotest_COLBUN = a0 + (a1 * Volumen) + (a2 * Volumen ** 2) + (a3 * Volumen ** 3) + (a4 * Volumen ** 4) + (a5 * Volumen ** 5)
    return Cotest_COLBUN


def dVol_COLBUN(Cota):
    a3 = 215.679132
    a2 = -564.993651
    a1 = 496.907289
    CMAX = 437
    VMAX = 1550.63
    dVol_Colbun = (a1 / CMAX + (2 * a2) * (Cota / CMAX) + (3 * a3) * (Cota / CMAX) ** 2) * VMAX
    return dVol_Colbun

def cot_colbun(Vol):
    cot_COLBUN=0.0
    
    if Vol <319.1:
        cot_COLBUN = 393
    elif Vol <380.22:
        y=[393,394,395,396,397]
        x=[319.1,333.76,348.83,364.32,380.22]      
        cota = interp1d(x,y)
        cot_COLBUN=cota(Vol)
    else:
        i=1
        error=0.005
        CotFin=10000
        CotIni=CotEST_COLBUN(Vol)
        while ((i<10) and (abs(CotFin-CotIni)>error)):
            i=i+1
            CotFin=CotIni-(vol_colbun(CotIni)-Vol)/dVol_COLBUN(CotIni)
            CotIni=CotFin
        cot_COLBUN=CotFin      
        
    return cot_COLBUN

"""
Funciones de cota de Cipreses

"""

def vol_cipreses(Cota):
    
    if Cota <1280:
        Vol_CIPRESES = 0
    else:
        a0 = 134744.88984
        a1 = -211.91025423
        a2 = 0.0833132678
        Vol_CIPRESES = a0 + (a1 * Cota) + (a2 * Cota ** 2)
        
    return Vol_CIPRESES


def cot_cipreses(Volumen):
    Cot_CIPRESES=0
    
    if Volumen <= 0:
        Cot_CIPRESES = 1280
    else:
        a0 = 134744.88984
        a1 = -211.91025423
        a2 = 0.0833132678
        DVol = (a1 * a1 - 4 * a2 * (a0 - Volumen)) ** 0.5
        Cot_CIPRESES = (-a1 + DVol) / (2 * a2)
        
    return Cot_CIPRESES



"""
Funciones de cota de El Toro

"""

def vol_eltoro(Cota):
    y=np.arange(1299,1371,1)   
    X=np.zeros(72)
    X[0]=0
    X[1] = 0
    X[2] = 48.28954
    X[3] = 97.47766
    X[4] = 147.26746
    X[5] = 197.35679
    X[6] = 248.04517
    X[7] = 299.43508
    X[8] = 351.82341
    X[9] = 405.0131
    X[10] = 459.20122
    X[11] = 514.48761
    X[12] = 570.97736
    X[13] = 628.56274
    X[14] = 687.35149
    X[15] = 747.53804
    X[16] = 808.92531
    X[17] = 871.61054
    X[18] = 935.59635
    X[19] = 1000.88273
    X[20] = 1067.4697
    X[21] = 1135.25477
    X[22] = 1204.23795
    X[23] = 1274.32464
    X[24] = 1345.60945
    X[25] = 1417.89268
    X[26] = 1491.07712
    X[27] = 1565.25999
    X[28] = 1640.4439
    X[29] = 1716.42655
    X[30] = 1793.41026
    X[31] = 1871.19533
    X[32] = 1949.97619
    X[33] = 2029.56105
    X[34] = 2110.14171
    X[35] = 2191.52373
    X[36] = 2273.9068
    X[37] = 2357.18845
    X[38] = 2441.47116
    X[39] = 2526.65244
    X[40] = 2612.83215
    X[41] = 2700.01554
    X[42] = 2788.19472
    X[43] = 2877.37496
    X[44] = 2967.75593
    X[45] = 3059.03548
    X[46] = 3151.31608
    X[47] = 3244.69758
    X[48] = 3339.17471
    X[49] = 3434.65552
    X[50] = 3531.13476
    X[51] = 3628.71226
    X[52] = 3727.4905
    X[53] = 3827.36962
    X[54] = 3928.44686
    X[55] = 4030.62499
    X[56] = 4133.90402
    X[57] = 4238.58084
    X[58] = 4344.35855
    X[59] = 4451.33437
    X[60] = 4559.61076
    X[61] = 4668.98805
    X[62] = 4779.66329
    X[63] = 4891.53927
    X[64] = 5004.41367
    X[65] = 5118.38896
    X[66] = 5233.46515
    X[67] = 5349.83928
    X[68] = 5467.31431
    X[69] = 5585.88761
    X[70] = 5705.66164
    X[71] = 5826.53656

    if Cota >=1370:
        Vol_ELTORO = 5826.53656
    elif Cota <1300:
        Vol_ELTORO=0
    else:     
        volumen = interp1d(y,X)
        Vol_ELTORO=volumen(Cota)
        
    return Vol_ELTORO


def cot_eltoro(Volumen):
    y=np.arange(1299,1371,1)   
    X=np.zeros(72)
    X[0]=0
    X[1] = 0
    X[2] = 48.28954
    X[3] = 97.47766
    X[4] = 147.26746
    X[5] = 197.35679
    X[6] = 248.04517
    X[7] = 299.43508
    X[8] = 351.82341
    X[9] = 405.0131
    X[10] = 459.20122
    X[11] = 514.48761
    X[12] = 570.97736
    X[13] = 628.56274
    X[14] = 687.35149
    X[15] = 747.53804
    X[16] = 808.92531
    X[17] = 871.61054
    X[18] = 935.59635
    X[19] = 1000.88273
    X[20] = 1067.4697
    X[21] = 1135.25477
    X[22] = 1204.23795
    X[23] = 1274.32464
    X[24] = 1345.60945
    X[25] = 1417.89268
    X[26] = 1491.07712
    X[27] = 1565.25999
    X[28] = 1640.4439
    X[29] = 1716.42655
    X[30] = 1793.41026
    X[31] = 1871.19533
    X[32] = 1949.97619
    X[33] = 2029.56105
    X[34] = 2110.14171
    X[35] = 2191.52373
    X[36] = 2273.9068
    X[37] = 2357.18845
    X[38] = 2441.47116
    X[39] = 2526.65244
    X[40] = 2612.83215
    X[41] = 2700.01554
    X[42] = 2788.19472
    X[43] = 2877.37496
    X[44] = 2967.75593
    X[45] = 3059.03548
    X[46] = 3151.31608
    X[47] = 3244.69758
    X[48] = 3339.17471
    X[49] = 3434.65552
    X[50] = 3531.13476
    X[51] = 3628.71226
    X[52] = 3727.4905
    X[53] = 3827.36962
    X[54] = 3928.44686
    X[55] = 4030.62499
    X[56] = 4133.90402
    X[57] = 4238.58084
    X[58] = 4344.35855
    X[59] = 4451.33437
    X[60] = 4559.61076
    X[61] = 4668.98805
    X[62] = 4779.66329
    X[63] = 4891.53927
    X[64] = 5004.41367
    X[65] = 5118.38896
    X[66] = 5233.46515
    X[67] = 5349.83928
    X[68] = 5467.31431
    X[69] = 5585.88761
    X[70] = 5705.66164
    X[71] = 5826.53656

    if Volumen >=5826.53656:
        Cot_ELTORO = 1370
    elif Volumen <0:
        Cot_ELTORO=1300
    else:     
        cota = interp1d(X,y)
        Cot_ELTORO=cota(Volumen)
        
    return Cot_ELTORO*1.0

"""
Funciones de cota de Machicura

"""

def vol_machicura(Cota):
    vol_MACHICURA=0.0
    
    if Cota <254.5:
        vol_MACHICURA = 0

    else:
        a0 = 0.220082
        a1 = 3.869693
        a2 = 0.854351
        a3 = -0.346473
        a4 = 0.080443
        a5 = -0.007131
        DCota = Cota - 254
        vol_MACHICURA = a0 + (a1 * DCota) + (a2 * DCota ** 2) + (a3 * DCota ** 3) + (a4 * DCota ** 4) + (a5 * DCota ** 5)
        
    return vol_MACHICURA

def CotEST_MACHICURA(Volumen):
    a0 = 253.9619
    a1 = 0.243919
    a2 = -0.006546
    a3 = 0.000503
    a4 = -0.000022
    a5 = 0.000000382368
    Cotest_MACHICURA = a0 + (a1 * Volumen) + (a2 * Volumen ** 2) + (a3 * Volumen ** 3) + (a4 * Volumen ** 4) + (a5 * Volumen ** 5)
    return Cotest_MACHICURA


def dVol_MACHICURA(Cota):
    a1 = 3.869693
    a2 = 0.854351
    a3 = -0.346473
    a4 = 0.080443
    a5 = -0.007131
    DCota = Cota - 254
    dvol_MACHICURA = (a1) + 2 * (a2 * DCota) + 3 * (a3 * DCota ** 2) + 4 * (a4 * DCota ** 3) + 5 * (a5 * DCota ** 4)
    return dvol_MACHICURA

def cot_machicura(Vol):
    cot_MACHICURA=0.0
    i=1
    error=0.005
    CotFin=10000
    CotIni=CotEST_MACHICURA(Vol)
    while ((i<10) and (abs(CotFin-CotIni)>error)):
            i=i+1
            CotFin=CotIni-(vol_machicura(CotIni)-Vol)/dVol_MACHICURA(CotIni)
            CotIni=CotFin
    cot_MACHICURA=CotFin      
        
    return cot_MACHICURA


"""
Funciones de cota de Laguna Maule

"""

def vol_lmaule(Cota):
    vol_LMAULE=0.0
    DCota = Cota - 2152.135
    a0 = -0.426511610904754
    a1 = 39.85091749344
    a2 = 0.713891558517388
    a3 = -2.68621789452889*(10**(-2))
    a4 = 7.69400535914122*(10**(-4))
    a5 = -8.51368088853222*(10**(-6))
    vol_LMAULE = max(0,a0 + (a1 * DCota) + (a2 * DCota ** 2) + (a3 * DCota ** 3) + (a4 * DCota ** 4) + (a5 * DCota ** 5))
        
    return vol_LMAULE

def CotEST_LMAULE(Volumen):
    a0 = 3.25854232403699*(10**(-3))
    a1 = 0.025405983908303
    a2 = -1.35727677749965*(10**(-5))
    a3 = 2.49264011608606*(10**(-8))
    a4 = -3.23135007234829*(10**(-11))
    a5 = 2.43385209187998*(10**(-14))
    a6 = -9.6847814254483*(10**(-18))
    a7 = 1.57390037611625*(10**(-21))
    Cotest_LMAULE = a0 + (a1 * Volumen) + (a2 * Volumen ** 2) + (a3 * Volumen ** 3) + (a4 * Volumen ** 4) + (a5 * Volumen ** 5)
    Cotest_LMAULE = Cotest_LMAULE + (a6 * Volumen ** 6) + (a7 * Volumen ** 7)
    Cotest_LMAULE = max(2180.3,Cotest_LMAULE + 2152.135)
    return Cotest_LMAULE

def dVol_LMAULE(Cota):
    DCota = Cota - 2152.135
    a0 = -0.426511610904754
    a1 = 39.85091749344
    a2 = 0.713891558517388
    a3 = -2.68621789452889*(10**(-2))
    a4 = 7.69400535914122*(10**(-4))
    a5 = -8.51368088853222*(10**(-6))
    dvol_LMAULE = (a1) + 2 * (a2 * DCota) + 3 * (a3 * DCota ** 2) + 4 * (a4 * DCota ** 3) + 5 * (a5 * DCota ** 4)
    return dvol_LMAULE

def cot_lmaule(Vol):
    cot_LMAULE=0.0
    i=1
    error=0.005
    CotFin=10000
    CotIni=CotEST_LMAULE(Vol)
    while ((i<10) and (abs(CotFin-CotIni)>error)):
            i=i+1
            CotFin=CotIni-(vol_lmaule(CotIni)-Vol)/dVol_LMAULE(CotIni)
            CotIni=CotFin
    cot_LMAULE=CotFin      
        
    return cot_LMAULE



"""
Funciones de cota de Pehuenche

"""

def vol_pehuenche(Cota):   
    a0 = 12532.0161
    a1 = -42.383595
    a2 = 0.0358801
    Vol_PEHUENCHE = a0 + (a1 * Cota) + (a2 * Cota ** 2)
        
    return Vol_PEHUENCHE


def cot_pehuenche(Volumen):
    a0 = 12532.0161
    a1 = -42.383595
    a2 = 0.0358801
    DVol = (a1 * a1 - 4 * a2 * (a0 - Volumen)) ** 0.5
    Cot_PEHUENCHE = (-a1 + DVol) / (2 * a2)
        
    return Cot_PEHUENCHE


"""
Funciones de cota de Pangue

"""

def vol_pangue(Cota):
        
    if Cota <493:
        Vol_PANGUE = 0
    else:
        a0 = 7091.6
        a1 = -32.43
        a2 = 0.0366
        Vol_PANGUE = max(0,a0 + a1 * Cota + a2 * Cota ** 2)
        
    return Vol_PANGUE


def cot_pangue(Volumen):
    a0 = 493
    a1 = 0.293889548
    a2 = -0.001273403
    a3 = 0.00000656608
    
    Cot_PANGUE = a0 + a1 * Volumen + a2 * Volumen ** 2 + a3 * Volumen ** 3
        
    return Cot_PANGUE

"""
Funciones de cota de Polcura

"""

def vol_polcura(Cota):
    a0 = 0.6976365827
    a1 = 90.859293303
    a2 = 40.08341237
    a3 = -13.9725593488
    a4 = 2.5864430194
    a5 = -0.159930272
    DCota = Cota - 730
    Vol_POLCURA = (a0 + (a1 * DCota) + (a2 * DCota ** 2) + (a3 * DCota ** 3) + (a4 * DCota ** 4) + (a5 * DCota ** 5)) / 1000
    return Vol_POLCURA

def CotEST_POLCURA(DVol):
    a0 = 730.02173
    a1 = 8.94574
    a2 = -8.50159
    a3 = 13.99204
    a4 = -13.87739
    a5 = 5.10665
    Cotest_POLCURA = a0 + (a1 * DVol) + (a2 * DVol ** 2) + (a3 * DVol ** 3) + (a4 * DVol ** 4) + (a5 * DVol ** 5)

    return Cotest_POLCURA


def dVol_POLCURA(Cota):
    a1 = 90.859293303
    a2 = 40.08341237
    a3 = -13.9725593488
    a4 = 2.5864430194
    a5 = -0.159930272
    DCota = Cota - 730
    dvol_POLCURA = ((a1) + 2 * (a2 * DCota) + 3 * (a3 * DCota ** 2) + 4 * (a4 * DCota ** 3) + 5 * (a5 * DCota ** 4)) / 1000
    return dvol_POLCURA

def cot_polcura(Vol):
    i=1
    error=0.005
    CotFin=10000
    CotIni=CotEST_POLCURA(Vol)
    while ((i<10) and (abs(CotFin-CotIni)>error)):
            i=i+1
            CotFin=CotIni-(vol_polcura(CotIni)-Vol)/dVol_POLCURA(CotIni)
            CotIni=CotFin
    cot_POLCURA=CotFin      
        
    return cot_POLCURA


"""
Funciones de cota de Ralco

"""

def vol_ralco(Cota): 
    X=np.zeros(9)
    Y=np.zeros(9)
    Y[0] = 0
    Y[1] = 0.02132
    Y[2] = 0.43767
    Y[3] = 4.90172
    Y[4] = 15.43637
    Y[5] = 22.730575
    Y[6] = 24.318677
    Y[7] = 25.984148
    Y[8] = 27.732006
    X[0] = 598
    X[1] = 600
    X[2] = 610
    X[3] = 620
    X[4] = 630
    X[5] = 635
    X[6] = 636
    X[7] = 637
    X[8] = 638
    a3 = 0.9869
    a2 = -72.676    
    a1 = 2789.6
    a0 = -30351

    if Cota <=X[8]:
        volumen = interp1d(X,Y)
        Vol_RALCO=volumen(Cota)
    elif Cota <X[0]:
        Vol_RALCO=0
    else:     
        Cota_R = Cota - X[0]
        Vol_RALCO = (a0 + a1 * Cota_R + a2 * Cota_R ** 2 + a3 * Cota_R ** 3) / 1000
        
    return Vol_RALCO

def dVol_dCot(Cota):
    a3 = 0.9869
    a2 = -72.676
    a1 = 2789.6
    Cota_R = Cota - 598
    dVol_dCot = (a1 + 2 * a2 * Cota_R + 3 * a3 * Cota_R ** 2) / 1000
    return dVol_dCot


def cot_ralco(Volumen):
    X=np.zeros(9)
    Y=np.zeros(9)
    Y[0] = 0
    Y[1] = 0.02132
    Y[2] = 0.43767
    Y[3] = 4.90172
    Y[4] = 15.43637
    Y[5] = 22.730575
    Y[6] = 24.318677
    Y[7] = 25.984148
    Y[8] = 27.732006
    X[0] = 598
    X[1] = 600
    X[2] = 610
    X[3] = 620
    X[4] = 630
    X[5] = 635
    X[6] = 636
    X[7] = 637
    X[8] = 638

    if Volumen <=Y[8]:
        cota = interp1d(Y,X)
        Cot_RALCO=cota(Volumen)
    elif Volumen <0:
        Cot_RALCO=598
    else:     
        Cota_R=708
        DCot=9999
        error=0.0001
        i=0
        while ((i<100) and (DCot>error)):
            i=i+1
            Vol_aux=vol_ralco(Cota_R)
            dVol_aux=dVol_dCot(Cota_R)
            Cota_A=Cota_R+(Volumen-Vol_aux)/dVol_aux
            DCot=abs(Cota_R-Cota_A)
            Cota_R=Cota_A
        Cot_RALCO=Cota_A
        
    return Cot_RALCO


"""
Funciones de cota de Rapel

"""

def vol_rapel(Cota):
    a0 = -36039.35
    a1 = 1279.686867
    a2 = -15.1802416
    a3 = 0.060121028
    Vol_RAPEL = max(65.3,a0 + (a1 * Cota) + (a2 * Cota ** 2) + (a3 * Cota ** 3))
    return Vol_RAPEL

def CotEST_RAPEL(Volumen):
    a0 = 89.57534303
    a1 = 0.45374052
    a2 = 0.02412212
    a3 = -0.00068196
    Cotest_RAPEL = a0 + (a1 * Volumen ** 0.5) + (a2 * Volumen) + (a3 * Volumen ** 1.5)

    return Cotest_RAPEL


def dVol_RAPEL(Cota):
    a1 = 1279.686867
    a2 = -15.1802416
    a3 = 0.060121028
    dvol_RAPEL = (a1) + 2 * (a2 * Cota) + 3 * (a3 * Cota ** 2)
    return dvol_RAPEL

def cot_rapel(Vol):
    i=1
    error=0.005
    CotFin=10000
    CotIni=CotEST_RAPEL(Vol)
    while ((i<10) and (abs(CotFin-CotIni)>error)):
            i=i+1
            CotFin=CotIni-(vol_rapel(CotIni)-Vol)/dVol_RAPEL(CotIni)
            CotIni=CotFin
    cot_RAPEL=CotFin      
        
    return cot_RAPEL

"""
Funciones de cota generales

"""

def cot_embalse(emb,vol):
    
    if emb == 'CIPRESES':
        return cot_cipreses(vol)
    elif emb == 'COLBUN':
        return cot_colbun(vol)
    elif emb == 'MACHICURA':
        return cot_machicura(vol)
    elif emb == 'PEHUENCHE':
        return cot_pehuenche(vol)
    elif emb == 'POLCURA':
        return cot_polcura(vol)
    elif emb == 'ELTORO':
        return cot_eltoro(vol)
    elif emb == 'ANGOSTURA':
        return cot_angostura(vol)
    elif emb == 'PANGUE':
        return cot_pangue(vol)
    elif emb == 'RALCO':
        return cot_ralco(vol)
    elif emb == 'CANUTILLAR':
        return cot_canutillar(vol)
    elif emb == 'RAPEL':
        return cot_rapel(vol)
    elif emb == 'L_Maule':
        return cot_lmaule(vol)
    else:
        return -1
    
