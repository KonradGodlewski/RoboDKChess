jQuery(function () {

    function getAiMove() {
        var moveReq = $.get("/ai");

        moveReq.done(function (data) {
            move = data.move;
            console.log("FEN move = ", move);
            console.log(data.message);
            updateDiag(data.message);
            if (data.win === "true") {
                handleWin(data);
                // check if loop checkbox is checked
                continueIfLoop();
            } else if (data.draw === "true") {
                handleDraw();
                continueIfLoop();
            } else if ($('#aiBtn').data('clicked')) {
                board.position(move);
                $('#aiBtn').data('clicked', false);
            } else {
                board.position(move);
                getAiMove();
            }
        });

        function continueIfLoop() {
            if ($('#loop').is(':checked')) {
                resetBoard();
            }
        }
    }

    function handleWin(data) {
        board.position(move);
        $('#aiBtn').prop('disabled', true);
        $('#collectBtn').prop('disabled', false);
        $('#turn').html(data.winner + ' Wins!\n');
        if (data.checkmate === "true") {
            updateDiag('Game ended: ' + data.winner + ' Wins! Checkmate! Promotions: ' + data.promotioncounter + '\n');
        } else {
            updateDiag('Game ended: ' + data.winner + ' Wins! Promotions: ' + data.promotioncounter + '\n');    
        }
    }

    function handleDraw() {
        $('#turn').html("Remis");
        $('#aiBtn').prop('disabled', true);
        $('#collectBtn').prop('disabled', false);
        updateDiag('Game ended: Draw\n');
    }

    function updateDiag(message) {
        txt = $('#diag');
        txt.val(txt.val() + message);
        if (txt.length)
            txt.scrollTop(txt[0].scrollHeight - txt.height());
    }

    function prepareBoard() {
        console.log("Board prepared");
        $("#aiBtn").prop('disabled', false);
        $('#turn').html("Game in progress..");
        $('#aiBtn').html('Stop Game');
        $('#collectBtn').prop('disabled', true);
        $('#aiBtn').data('clicked', false);
        $("#aiBtn").off('click').on('click', secondClick)
        getAiMove();
    }

    function firstClick() {
        board.start(true);
        $("#aiBtn").prop('disabled', true);
        $('#turn').html("Preparing..");
        $.get("/prepareBoard", prepareBoard);
    }

    function secondClick() {
        $('#aiBtn').html('Resume Game');
        $('#turn').html("Game stopped");
        $('#aiBtn').data('clicked', true);
        $('#collectBtn').prop('disabled', false);
        $("#aiBtn").off('click').on('click', thirdClick)
    }

    function thirdClick() {
        $('#aiBtn').html('Stop Game');
        $('#turn').html("Game in progress..");
        $('#collectBtn').prop('disabled', true);
        $('#aiBtn').data('clicked', false);
        $("#aiBtn").off('click').on('click', secondClick)
        getAiMove();
    }

    function resetBoard() {
        $('#turn').html("Sprzątanie..");
        $('#aiBtn').prop('disabled', true);
        $('#collectBtn').prop('disabled', true);
        updateDiag('-------------------\n');
        $.get("/collectPieces", function(){
            $('#aiBtn').prop('disabled', false);
            $('#turn').html("Click button to start");
            $('#aiBtn').html('Start Game');
            $("#aiBtn").off('click').on('click', firstClick);
            $('#collectBtn').prop('disabled', true);
            board.start(true)
            if ($('#loop').is(':checked')) {
                countdownBeforeStartNewGane().then(firstClick);
            }
        });
    }

    // countdown before start new game, write update every second
    // synchronous, so it will wait until the function is finished
    function countdownBeforeStartNewGane() {
        $('#aiBtn').prop('disabled', true);
        var defer = $.Deferred();
        var count = 5;
        var timer = setInterval(function () {
            count--;
            $('#turn').html("New game in: " + count);
            if (count === 0) {
                clearInterval(timer);
                defer.resolve();
            }

        }, 1000);
        return defer.promise();
    }

    var boardElement = $('#myBoard');

    var config ={
        position: 'start',
        pieceTheme :'static/img/chesspieces/wikipedia/{piece}.png',
        draggable: false,
        sparePieces: false,
    };

    var board = Chessboard(boardElement, config);
    $('#collectBtn').prop('disabled', true);
    $('#aiBtn').click(firstClick)
    $('#collectBtn').click(resetBoard);
    //resetBoard();
})