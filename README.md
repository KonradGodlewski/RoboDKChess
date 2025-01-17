# RoboDK chess
A game of chess played by two chess engines that can be previewed in the **browser**. Every move is performed by the robot in **RoboDK** and then the **real robot** replicates the robot movement from the simulation.

This solution allows for the robot to play an entire game of chess including putting pieces on the chessboard before the game starts and putting them back to the side once the game is finished. The robot can also play multiple games one after the other by toggling the loop checkbox.

Altough there are two robots in the videos, the current version of the programm only uses one robot to move both black and white pieces. 

Board preperation:
<br/>
![Gif3](https://github.com/user-attachments/assets/80013068-f813-4a26-9435-94684f66ba76)
<br/>

Fragment of a game:
<br/>
![Gif2](https://github.com/user-attachments/assets/2e1813c3-e110-473a-ad09-503f66b19c4e)
<br/>

Real robot:
<br/>
![Gif4](https://github.com/user-attachments/assets/25ffc048-c87f-4600-b985-ff55f52ab1b9)
<br/>

## Prerequisites
* [RoboDK](https://robodk.com/)
* RTToolbox (for simulation) or real robot (Used in the project is Mitsubishi RV-2FR)
  

## Getting started
### Python script
Run python script (**MitsubishiChess.py**) and go to the address **localhost:5000** in the web browser. You should see a empty chessboard. Press the login button below the chessboard and proceed to login (user:admin,password:admin123 (it can be changed in the **MitsubishiChess.py** script in line 14))
### Robot/Simulation
Set up the robot parameters like shown in the picture below (Port number may vary, just have to be the same in both robot parameters and **MitsubishiChess.py** script (line 216)

![Parameters](https://github.com/user-attachments/assets/03fe2e95-be21-432d-bc3d-ccc253bd2d5c)

Make sure that the robot is in the same network as the pc to establish connetcion between them. Change the IP address to the one you are using in the **MitsubishiChess.py** script (line 215)
If you're using RTToolbox only for simulation, then the IP address is the same as the IP address of your PC.
At this point run the **MELFA_script** on a robot or in the simulator. 

## Game of chess
Once everything is set up go back to the browser, press **start game** and enjoy the results.

