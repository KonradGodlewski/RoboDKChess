import random
import os
from flask import Flask, render_template, request, Response, make_response, jsonify, session, redirect, url_for
from robodk import *    # RoboDK API
from robodk import *    # Robot toolbox
import chess
import chess.engine
import logging
import uuid
import socket
import time

users = {
    'admin': {'password': 'admin123'},
}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure secret key
active_sessions = {}  # Dictionary to store active sessions

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
board = chess.Board()
stockfish_path = 'stockfish'
cinnamon_path = 'cinnamon'
stockfish = chess.engine.SimpleEngine.popen_uci(stockfish_path)
cinnamon = chess.engine.SimpleEngine.popen_uci(cinnamon_path)
maxmoves = 150
z = -50
hoverHeight = 40
descentHeight = 63
hoverGraveyard = 45
descentGraveyard = 80
class State:
    def __init__(self):
        self.wPawnXLocation = 0
        self.wKnightXLocation = 37.5
        self.wBishopXLocation = 75
        self.wRookXLocation = 0
        self.wQueenXLocation = 112.5
        self.wKingXLocation = 150
        self.wTakenPieceLocation = 0
        self.bPawnXLocation = 0
        self.bKnightXLocation = 37.5
        self.bBishopXLocation = 75
        self.bRookXLocation = 0
        self.bQueenXLocation = 112.5
        self.bKingXLocation = 150
        self.bTakenPieceLocation = 0
        self.extraBlackQueen = 0
        self.extraWhiteQueen = 0
        self.movecounter = 0
        self.wPromotioncounter = 0
        self.bPromotioncounter = 0
        self.state = 'init'
        self.fen = ''

game_state=State()

RDK = robolink.Robolink()
gripperMitsubishi = RDK.Item('MitsubishiMechanism')
robotMitsubishi = RDK.Item('Mitsubishi RV-2FR') 
dictsidetomove = {  True: {'color': 'white', 'robot': robotMitsubishi},
                    False: {'color': 'black', 'robot': robotMitsubishi}  }

@app.route("/prepareBoard",methods = ['POST','GET'])
def PutPiecesOnBoard():
    game_state.state = 'prep'
    PrepareBoard(robotMitsubishi,'black')
    PrepareBoard(robotMitsubishi,'white')
    game_state.state = 'ready'
    game_state.fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'
    return {}

@app.route("/collectPieces",methods = ['POST','GET'])
def collectPieces():
    game_state.state = 'collect'
    ClearChessBoard('white')
    ClearChessBoard('black')
    board.reset()
    RDK.Item('ResetPiecesHolders').RunProgram()
    game_state.state = 'init'
    game_state.fen = ''
    game_state.__init__()
    return {}

@app.route("/stat",methods=['POST','GET'])
def stat():
    returnDict = {}
    returnDict['state'] = game_state.state
    returnDict['fen'] = game_state.fen
    return returnDict

@app.route("/", methods=['POST','GET'])
def chessServer():
    user_id = session.get('user_id')
    if user_id in active_sessions:
        return render_template('index1.html',  username=active_sessions[user_id], state=game_state.state, fen=game_state.fen, static_url_path='')
    return render_template('index1.html', state=game_state.state, fen=game_state.fen, static_url_path='')    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('chessServer'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in active_sessions:
            return 'Already logged in. Only one admin session allowed. Log off existing session first.'

        if username in users and password == users[username]['password']:
            session_id = str(uuid.uuid4())
            session['username'] = username
            active_sessions[username] = session_id
            return redirect(url_for('chessServer'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('username')
    if username:
        active_sessions.pop(username, None)
        session.pop('username', None)
    return redirect(url_for('chessServer'))

@app.route("/ai", methods=['GET'])
def getAImove():
    returnDict = {}
    game_state.state = 'move'
    if(board.turn):
        result = stockfish.play(board,chess.engine.Limit(depth=int(random.uniform(10, 15)), time=1))
        game_state.movecounter += 1
    else:
        result = cinnamon.play(board,chess.engine.Limit(depth=5, time=1))
    f = open("test.txt", "a")
    f.write(board.lan(result.move) + "\n")
    f.close()
    print(board.lan(result.move))
    if '=' in board.lan(result.move):
        if(board.turn):
            game_state.wPromotioncounter += 1
        else:   
            game_state.bPromotioncounter += 1
        if '=Q' not in board.lan(result.move):
            result.move = chess.Move(result.move.from_square, result.move.to_square, chess.QUEEN)

    f = open("test.txt", "a")
    f.write(board.lan(result.move) + "\n")
    f.close()
    
    if game_state.wPromotioncounter == 2 or game_state.bPromotioncounter == 2:
        returnDict['winner'] = "White" if game_state.wPromotioncounter == 2 else "Black"
        returnDict['win'] = 'true'
        returnDict['wPromotioncounter'] = game_state.wPromotioncounter
        returnDict['bPromotioncounter'] = game_state.bPromotioncounter
        game_state.state = 'win'
        return returnDict
    
    robot_move_instructions = robotMove(game_state.movecounter, board.lan(result.move), dictsidetomove[board.turn]['robot'], dictsidetomove[board.turn]['color'], result.move)
    returnDict["message"] = robot_move_instructions
    board.push(result.move)
    returnDict['move'] = str(board.fen())
    game_state.fen = str(board.fen())
    if(game_state.movecounter >= maxmoves):
        returnDict["draw"] = 'true'
        game_state.state = 'win'
        return returnDict
    
    if(board.is_checkmate()):
        returnDict['checkmate'] = 'true'
        game_state.state = 'win'
        returnDict = returnWin(returnDict)
        return returnDict
    
    game_state.state = 'ready'
    return returnDict

def returnWin(returnDict):
    winner = board.outcome().winner
    if(winner == False):
        winner = "Black"
    else:
        winner = "White"
    returnDict['winner'] = winner
    returnDict['win']= 'true'
    returnDict['wPromotioncounter'] = game_state.wPromotioncounter
    returnDict['bPromotioncounter'] = game_state.bPromotioncounter
    return returnDict

def set_robot_parameters(color):
    if color == 'white':
        pieceHolder = RDK.Item('BlackPieceHolder')
        graveYardStart = RDK.Item('GraveyardMA')
    else:
        graveYardStart = RDK.Item('GraveyardM')
        pieceHolder = RDK.Item('WhitePieceHolder')
    refPoint = RDK.Item('A1')
    home = RDK.Item('HomeMitsubishi')
    robottool = RDK.Item('4F-MEHGR-05M')
    return refPoint, home, robottool, graveYardStart, pieceHolder

def getJoints(robot):
    joints = robot.Joints()
    J1 = str(joints[0,0])
    J2 = str(joints[1,0])
    J3 = str(joints[2,0])
    J4 = str(joints[3,0])
    J5 = str(joints[4,0])
    J6 = str(joints[5,0])
    return J1,J2,J3,J4,J5,J6
def sendData(robot,hand):
    J1,J2,J3,J4,J5,J6 = getJoints(robot)
    HOST = '192.168.72.13'
    PORT = 10003
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST,PORT))
        s.send(bytes(J1+','+J2+','+J3+','+J4+','+J5+','+J6+','+str(hand), encoding='utf-8'))
        data = s.recv(1024)
        data = int(data)
        print('Received',repr(data))
        while data != 1:
            pause(0.1)
            data = s.recv(1024)
            data = int(data)

def robotMove(movecounter,move,robot,color,result): #Move the robot
    refPoint, home, robottool, graveYardStart, pieceHolder = set_robot_parameters(color)
    message = ''
    castlings = {
        'O-O+': [('e1', 'g1'), ('h1', 'f1')] if color == 'white' else [('e8', 'g8'), ('h8', 'f8')],
        'O-O-O+': [('e1', 'c1'), ('a1', 'd1')] if color == 'white' else [('e8', 'c8'), ('a8', 'd8')],
        'O-O': [('e1', 'g1'), ('h1', 'f1')] if color == 'white' else [('e8', 'g8'), ('h8', 'f8')],
        'O-O-O': [('e1', 'c1'), ('a1', 'd1')] if color == 'white' else [('e8', 'c8'), ('a8', 'd8')]
    }
    if move in castlings:
            castlingCnt = 0
            for castling_move in castlings[move]:
                start_position = castling_move[0]
                end_position = castling_move[1]
                message += ( f'{movecounter}. CASTLING: Robot {color} moved figure from {start_position} to {end_position}\n')
                start = [start_position[0],start_position[1]]
                end = [end_position[0],end_position[1]]
                xs, ys, xe, ye = calculateCoordinates(color, start, end)
                robot.MoveJ(refPoint.Pose()*transl(xs,ys,z+hoverHeight))
                OpenGripper('black')
                sendData(robotMitsubishi,1)
                robot.MoveL(refPoint.Pose()*transl(xs,ys,0+descentHeight))
                CloseGripper('black')
                sendData(robotMitsubishi,0)
                robottool.AttachClosest()
                robot.MoveL(refPoint.Pose()*transl(xs,ys,z+hoverHeight)) if castlingCnt == 0 else robot.MoveL(refPoint.Pose()*transl(xs,ys,2*z+hoverHeight))
                sendData(robotMitsubishi,0)
                robot.MoveJ(refPoint.Pose()*transl(xe,ye,z+hoverHeight)) if castlingCnt == 0 else robot.MoveL(refPoint.Pose()*transl(xe,ye,2*z+hoverHeight))
                sendData(robotMitsubishi,0)
                robot.MoveL(refPoint.Pose()*transl(xe,ye,0+descentHeight))
                OpenGripper('black')
                sendData(robotMitsubishi,1)
                robottool.DetachAll(RDK.Item('ChessBoardFull'))
                robot.MoveL(refPoint.Pose()*transl(xe,ye,2*z+descentHeight)) if castlingCnt == 0 else robot.MoveL(refPoint.Pose()*transl(xe,ye,z+descentHeight))
                sendData(robotMitsubishi,1)
                castlingCnt = 1
            return message
    elif '-' in move or 'x' in move:
        positions = move.split('-' if '-' in move else 'x')
        start_position = positions[-2][-2:]
        end_position = positions[-1][:2]
        start = [start_position[0],start_position[1]]
        end = [end_position[0],end_position[1]]
        piece = CapturedPiece(board,result)
        updateLocation = UpdateHolderLocation(piece,color)
        yOff = 0 if piece > 1 else 38.125
        if color == 'black':
            yOff = -yOff
        updateLocation = -updateLocation
        xs, ys, xe, ye = calculateCoordinates(color, start, end)

        if 'x' in move:
            message += (f'{movecounter}. CAPTURE: Robot {color} moved figure from {end_position} to the holder\n')
            if board.is_en_passant(result):
                robot.MoveJ(refPoint.Pose()*transl(xe-37.5,ye,z+hoverHeight)) if color == 'white' else robot.MoveJ(refPoint.Pose()*transl(xe-37.5,ye,z+hoverHeight))
                OpenGripper('black')
                sendData(robotMitsubishi,1)
                robot.MoveL(refPoint.Pose()*transl(xe-37.5,ye,0+descentHeight)) if color == 'white' else robot.MoveJ(refPoint.Pose()*transl(xe-37.5,ye,0+descentHeight))
                CloseGripper('black')
                sendData(robotMitsubishi,0)
                robottool.AttachClosest()
                robot.MoveL(refPoint.Pose()*transl(xe-37.5,ye,z+hoverHeight)) if color == 'white' else robot.MoveL(refPoint.Pose()*transl(xe-37.5,ye,z+hoverHeight))
                sendData(robotMitsubishi,0)
            else:
                robot.MoveJ(refPoint.Pose()*transl(xe,ye,z+hoverHeight))
                OpenGripper('black')
                sendData(robotMitsubishi,1)
                robot.MoveL(refPoint.Pose()*transl(xe,ye,0+descentHeight))
                CloseGripper('black')
                sendData(robotMitsubishi,0)                
                robottool.AttachClosest()
                robot.MoveL(refPoint.Pose()*transl(xe,ye,z+hoverHeight))
                sendData(robotMitsubishi,0)
            if piece == 2:
                robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard)*rotz(1.570796))
                sendData(robotMitsubishi,0)
                robot.MoveL(graveYardStart.Pose()*transl(updateLocation,yOff,0+descentGraveyard)*rotz(1.570796))
                OpenGripper('black')
                sendData(robotMitsubishi,1)
                robottool.DetachAll(pieceHolder)
                robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverHeight))
                sendData(robotMitsubishi,1)
            else:
                robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                sendData(robotMitsubishi,0)
                robot.MoveL(graveYardStart.Pose()*transl(updateLocation,yOff,0+descentGraveyard))
                OpenGripper('black')
                sendData(robotMitsubishi,1)
                robottool.DetachAll(pieceHolder)
                robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverHeight))
                sendData(robotMitsubishi,1)
        message += (f'{movecounter}. MOVE: Robot {color} moved figure from {start_position} to {end_position}\n')
        robot.MoveJ(refPoint.Pose()*transl(xs,ys,z+hoverHeight))
        OpenGripper('black')
        sendData(robotMitsubishi,1)
        robot.MoveL(refPoint.Pose()*transl(xs,ys,0+descentHeight))
        CloseGripper('black')
        sendData(robotMitsubishi,0)
        robottool.AttachClosest()
        robot.MoveL(refPoint.Pose()*transl(xs,ys,z+hoverHeight))
        sendData(robotMitsubishi,0)
        robot.MoveJ(refPoint.Pose()*transl(xe,ye,z+hoverHeight))
        sendData(robotMitsubishi,0)
        robot.MoveL(refPoint.Pose()*transl(xe,ye,0+descentHeight))
        OpenGripper('black')
        sendData(robotMitsubishi,1)
        robottool.DetachAll(RDK.Item('ChessBoardFull'))
        robot.MoveL(refPoint.Pose()*transl(xe,ye,z+hoverHeight))
        sendData(robotMitsubishi,1)
        if '=' in move:
            message += (f'{movecounter}. PROMOTION: Robot {color} promoted Pawn to Queen\n')
            piece = 1
            yOff = 38.125
            if color == 'white':
                updateLocation = UpdateHolderLocation(piece,'black')
                extraQX = game_state.wQueenXLocation
                extraQY = 38.125
                Promotion('black',xe,ye,-yOff,-updateLocation,-extraQX,extraQY)
            else:
                updateLocation = UpdateHolderLocation(piece,'white')
                extraQX = game_state.bQueenXLocation
                extraQY = -38.125
                Promotion('white',-xe,-ye,yOff,-updateLocation,-extraQX,extraQY)
        return message

def calculateCoordinates(color, start, end):
    xs = ((int(start[1]) -1 ) * 37.5)
    ys = (((ord(start[0])-96) -1) * 38.125)
    xe = ((int(end[1]) -1 ) * 37.5)
    ye = (((ord(end[0])-96) -1) * 38.125)
    xs = -xs
    ys = -ys
    xe = -xe
    ye = -ye
    return xs,ys,xe,ye
        
def OpenGripper(color): #Close the gripper
    if color == 'black':
        gripperMitsubishi.MoveJ(RDK.Item('OpenM'))

def CloseGripper(color): # Close the gripper
    if color == 'black':
        gripperMitsubishi.MoveJ(RDK.Item('CloseM'))

def PrepareBoard(robot,color): # Take pieces from holders and place them on the chessboard
    ref = RDK.Item('GraveyardMA') if color == 'white' else RDK.Item('GraveyardM')
    point = RDK.Item('A1')
    robottool = RDK.Item('4F-MEHGR-05M')
    for counter in range(16):
        yO = 0 if counter <8 else 38.125
        xO = counter * 37.5 if yO == 0 else (counter-8) * 37.5
        x1 = 262.5 if counter < 8 else 225
        y1 = counter * 38.125 if x1 == 262.5 else (counter-8) * 38.125 
        if color == 'black': 
            yO = -yO
            xO = -xO
            y1 = -y1
            x1 = 0 if counter < 8 else -37.5
        else: 
            xO = -xO
            x1 = -x1
            y1 = -y1
        robot.MoveJ(ref.Pose()*transl(xO,yO,z+hoverGraveyard))
        OpenGripper('black')
        sendData(robotMitsubishi,1)
        robot.MoveL(ref.Pose()*transl(xO,yO,0+descentGraveyard))
        CloseGripper('black')
        sendData(robotMitsubishi,0)
        robottool.AttachClosest()
        robot.MoveL(ref.Pose()*transl(xO,yO,z+hoverGraveyard))
        sendData(robotMitsubishi,0)   
        robot.MoveJ(point.Pose()*transl(x1,y1,z+hoverHeight)*rotz(-1.570796))
        sendData(robotMitsubishi,0)
        robot.MoveL(point.Pose()*transl(x1,y1,0+descentHeight)*rotz(-1.570796))
        OpenGripper('black')
        sendData(robotMitsubishi,1)
        robottool.DetachAll(RDK.Item('ChessBoardFull'))
        # robot.MoveJ(point.Pose()*transl(x1,y1,z+hoverHeight)) if counter == 1 and color == 'white' or 6 and color == 'white' else robot.MoveJ(point.Pose()*transl(x1,y1,z+hoverHeight))
        robot.MoveJ(point.Pose()*transl(x1,y1,z+hoverHeight))
        sendData(robotMitsubishi,1)
    robot.MoveJ(RDK.Item('HomeMitsubishi'))
    sendData(robotMitsubishi,0)

def CapturedPiece(board, move): # Check whether the piece was captured and return the piece if it was
    if board.is_capture(move):
        if board.is_en_passant(move):
            return chess.PAWN
        else:
            return board.piece_at(move.to_square).piece_type
    return 0

def UpdateHolderLocation(value,color): # Set the position value of pieces in the holders
    pieces = {1 : 'Pawn',
              2 : 'Knight',
              3 : 'Bishop',
              4 : 'Rook',
              5 : 'Queen',
              6 : 'King'
    }
    if int(value) == 1:
        if color == 'black':
            game_state.wTakenPieceLocation = game_state.wPawnXLocation
            game_state.wPawnXLocation += 37.5
        else:
            game_state.bTakenPieceLocation = game_state.bPawnXLocation
            game_state.bPawnXLocation += 37.5
    elif int(value) == 2:
        if color == 'black':
            game_state.wTakenPieceLocation = game_state.wKnightXLocation
            game_state.wKnightXLocation += 187.5
        else:
            game_state.bTakenPieceLocation = game_state.bKnightXLocation
            game_state.bKnightXLocation += 187.5
    elif int(value) == 3:
        if color == 'black':
            game_state.wTakenPieceLocation = game_state.wBishopXLocation
            game_state.wBishopXLocation += 112.5
        else:
            game_state.bTakenPieceLocation = game_state.bBishopXLocation
            game_state.bBishopXLocation += 112.5
    elif int(value) == 4:
        if color == 'black':
            game_state.wTakenPieceLocation = game_state.wRookXLocation
            game_state.wRookXLocation += 262.5
        else:
            game_state.bTakenPieceLocation = game_state.bRookXLocation
            game_state.bRookXLocation += 262.5
    elif int(value) == 5:
        if color == 'black':
            game_state.wTakenPieceLocation = game_state.wQueenXLocation
            game_state.extraWhiteQueen += 1
        else:
            game_state.bTakenPieceLocation = game_state.bQueenXLocation
            game_state.extraBlackQueen += 1

    elif int(value) == 6:
        if color == 'black':
            game_state.wTakenPieceLocation = game_state.wKingXLocation
        else: game_state.bTakenPieceLocation = game_state.bKingXLocation
    return game_state.wTakenPieceLocation if color == 'black' else game_state.bTakenPieceLocation

def ClearChessBoard(color): #Collecting remaining pieces from the chessboard

    robot = RDK.Item('Mitsubishi RV-2FR')
    refPoint, home, robottool, graveYardStart, pieceHolder = set_robot_parameters(color)

    for i in range(64):
        square = chess.SQUARES[i]
        newsquare = chess.square_name(square)
        piece = board.piece_at(square)
        if piece != None:
            pieceType = piece.piece_type
            pieceColor = 'white' if piece.color else 'black'
            message = ( f'{i}. Piece: {piece} PieceType: {pieceType} PieceColor: {pieceColor}\n')     
            start_position = str(newsquare)
            start = [start_position[0],start_position[1]]
            xs = ((int(start[1]) -1 ) * 37.5)
            ys = (((ord(start[0])-96) -1) * 38.125)
            yOff = 0 if pieceType > 1 else 38.125
            xs = -xs
            ys = -ys
            if color == 'white' and pieceColor == 'black':
                updateLocation = UpdateHolderLocation(pieceType,color)
                updateLocation = -updateLocation
                robot.MoveJ(refPoint.Pose()*transl(xs,ys,z+hoverHeight))
                OpenGripper('black')
                sendData(robotMitsubishi,1)
                robot.MoveL(refPoint.Pose()*transl(xs,ys,0+descentHeight))
                CloseGripper('black')
                sendData(robotMitsubishi,0)
                robottool.AttachClosest()
                robot.MoveL(refPoint.Pose()*transl(xs,ys,z+hoverHeight))
                sendData(robotMitsubishi,0)
                if pieceType == 2:
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard)*rotz(1.570796))
                    CloseGripper('black')
                    sendData(robotMitsubishi,0)
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,0+descentGraveyard)*rotz(1.570796))
                    OpenGripper('black')
                    sendData(robotMitsubishi,1)
                    robottool.DetachAll(pieceHolder)
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                    sendData(robotMitsubishi,1)
                elif pieceType == 5 and game_state.extraBlackQueen == 2:
                    yOff = -38.125
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                    CloseGripper('black')
                    sendData(robotMitsubishi,0)
                    robot.MoveL(graveYardStart.Pose()*transl(updateLocation,yOff,0+descentGraveyard))
                    OpenGripper('black')
                    sendData(robotMitsubishi,1)
                    robottool.DetachAll(pieceHolder)
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                    sendData(robotMitsubishi,1)
                else:  
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                    CloseGripper('black')
                    sendData(robotMitsubishi,0)
                    robot.MoveL(graveYardStart.Pose()*transl(updateLocation,yOff,0+descentGraveyard))
                    OpenGripper('black')
                    sendData(robotMitsubishi,1)
                    robottool.DetachAll(pieceHolder)
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                    sendData(robotMitsubishi,1)
            elif color == 'black' and pieceColor == 'white':
                yOff = -yOff
                updateLocation = UpdateHolderLocation(pieceType,color)
                updateLocation = -updateLocation
                robot.MoveJ(refPoint.Pose()*transl(xs,ys,z+hoverHeight))
                OpenGripper('black')
                sendData(robotMitsubishi,1)
                robot.MoveL(refPoint.Pose()*transl(xs,ys,0+descentHeight))
                CloseGripper('black')
                sendData(robotMitsubishi,0)
                robottool.AttachClosest()
                robot.MoveL(refPoint.Pose()*transl(xs,ys,z+hoverHeight))
                sendData(robotMitsubishi,0)
                if pieceType == 2:
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard)*rotz(1.570796))
                    CloseGripper('black')
                    sendData(robotMitsubishi,0)
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,0+descentGraveyard)*rotz(1.570796))
                    OpenGripper('black')
                    sendData(robotMitsubishi,1)
                    robottool.DetachAll(pieceHolder)
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                    sendData(robotMitsubishi,1)
                elif pieceType == 5 and game_state.extraWhiteQueen == 2:
                    yOff = 38.125
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                    CloseGripper('black')
                    sendData(robotMitsubishi,0)
                    robot.MoveL(graveYardStart.Pose()*transl(updateLocation,yOff,0+descentGraveyard))
                    OpenGripper('black')
                    sendData(robotMitsubishi,1)
                    robottool.DetachAll(pieceHolder)
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                    sendData(robotMitsubishi,1)
                else:
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                    CloseGripper('black')
                    sendData(robotMitsubishi,0)
                    robot.MoveL(graveYardStart.Pose()*transl(updateLocation,yOff,0+descentGraveyard))
                    OpenGripper('black')
                    sendData(robotMitsubishi,1)
                    robottool.DetachAll(pieceHolder)
                    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
                    sendData(robotMitsubishi,1)
    robot.MoveJ(home)
    sendData(robotMitsubishi,0)
    return message

def Promotion(color,xe,ye,yOff,updateLocation,extraQX,extraQY): #Removing a pawn from the chessboard and placing a queen
    robot = RDK.Item('Mitsubishi RV-2FR')
    refPoint, home, robottool, graveYardStart, pieceHolder = set_robot_parameters(color)
    print(color,xe,ye,yOff,updateLocation,extraQX,extraQY)

    robot.MoveJ(refPoint.Pose()*transl(xe,ye,z+hoverHeight))
    OpenGripper('black')
    sendData(robotMitsubishi,1)
    robot.MoveL(refPoint.Pose()*transl(xe,ye,0+descentHeight))
    CloseGripper('black')
    sendData(robotMitsubishi,0)
    robottool.AttachClosest()
    robot.MoveL(refPoint.Pose()*transl(xe,ye,z+hoverHeight))
    sendData(robotMitsubishi,0)
    robot.MoveJ(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
    sendData(robotMitsubishi,0)
    robot.MoveL(graveYardStart.Pose()*transl(updateLocation,yOff,0+descentGraveyard))
    OpenGripper('black')
    sendData(robotMitsubishi,1)
    robottool.DetachAll(pieceHolder)
    robot.MoveL(graveYardStart.Pose()*transl(updateLocation,yOff,z+hoverGraveyard))
    sendData(robotMitsubishi,1)
    robot.MoveJ(graveYardStart.Pose()*transl(extraQX,extraQY,z+hoverGraveyard))
    sendData(robotMitsubishi,1)
    robot.MoveL(graveYardStart.Pose()*transl(extraQX,extraQY,0+descentGraveyard))
    CloseGripper('black')
    sendData(robotMitsubishi,0)
    robottool.AttachClosest()
    robot.MoveL(graveYardStart.Pose()*transl(extraQX,extraQY,z+hoverGraveyard))
    sendData(robotMitsubishi,0)
    robot.MoveJ(refPoint.Pose()*transl(xe,ye,z+hoverHeight))
    sendData(robotMitsubishi,0)
    robot.MoveL(refPoint.Pose()*transl(xe,ye,0+descentHeight))
    OpenGripper('black')
    sendData(robotMitsubishi,1)
    robottool.DetachAll(RDK.Item('ChessBoardFull'))
    robot.MoveL(refPoint.Pose()*transl(xe,ye,z+hoverHeight))
    sendData(robotMitsubishi,1)

if __name__ == "__main__":
    app.run(debug=False)
