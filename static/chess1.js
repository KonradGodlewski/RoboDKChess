jQuery(function () {
    var move;

    function getAiMove() {
        $.get("/ai")
            .done(function (data) {
                move = data.move;
                // console.log("FEN move = ", move);
                // console.log(data.message);
                updateDiag(data.message);
                if (data.win === "true") {
                    handleWin(data);
                    continueIfLoop();
                } else if (data.draw === "true") {
                    handleDraw();
                    continueIfLoop();
                } else if ($('#aiBtn').data('clicked')) {
                    board.position(move);
                    $('#aiBtn').data('clicked', false);
                    $('#collectBtn').prop('disabled', false);
                } else {
                    board.position(move);
                    getAiMove();
                }
            });
    }

    function continueIfLoop() {
        if ($('#loop').is(':checked')) {
            resetBoard();
        }
    }

    function handleWin(data) {
        board.position(move);
        $('#aiBtn').prop('disabled', true);
        $('#collectBtn').prop('disabled', false);
        $('#turn').html(data.winner + ' Wins!\n');
        var message = 'Game ended: ' + data.winner + ' Wins!';
        if (data.checkmate === "true") {
            message += ' Checkmate! Promotions: W - ' + data.wPromotioncounter + ', B - ' + data.bPromotioncounter;
        } else {
            message += ' Promotions: W - ' + data.wPromotioncounter + ', B - ' + data.bPromotioncounter;
        }
        updateDiag(message + '\n');
    }

    function handleDraw() {
        $('#turn').html("Remis");
        $('#aiBtn').prop('disabled', true);
        $('#collectBtn').prop('disabled', false);
        updateDiag('Game ended: Draw\n');
    }

    function updateDiag(message) {
        var txt = $('#diag');
        txt.val(txt.val() + message);
        if (txt.length) {
            txt.scrollTop(txt[0].scrollHeight - txt.height());
        }
    }

    function prepareBoard() {
        // console.log("Board prepared");
        $("#aiBtn").prop('disabled', false);
        $('#turn').html("Game in progress..");
        $('#aiBtn').html('Stop Game');
        $('#collectBtn').prop('disabled', true);
        $('#aiBtn').data('clicked', false);
        $("#aiBtn").off('click').on('click', secondClick);
        updateDiag('----------Starting new game----------\n');
        getAiMove();
    }

    function firstClick() {
        $("#aiBtn").prop('disabled', true);
        $('#turn').html("Preparing..");
        $.get("/prepareBoard", prepareBoard);
    }

    function secondClick() {
        $('#aiBtn').html('Resume Game');
        $('#turn').html("Game stopped");
        $('#aiBtn').data('clicked', true);
        $("#aiBtn").off('click').on('click', thirdClick);
    }

    function thirdClick() {
        $('#aiBtn').html('Stop Game');
        $('#turn').html("Game in progress..");
        $('#collectBtn').prop('disabled', true);
        $('#aiBtn').data('clicked', false);
        $("#aiBtn").off('click').on('click', secondClick);
        getAiMove();
    }

    function resetBoard() {
        $('#turn').html("Sprzątanie..");
        $('#aiBtn').prop('disabled', true);
        $('#collectBtn').prop('disabled', true);

        $.get("/collectPieces")
        .done(function () {
            $('#aiBtn').prop('disabled', false);
            $('#collectBtn').prop('disabled', true);
            $('#turn').html("Click button to start");
            $('#aiBtn').html('Start Game');
            $("#aiBtn").off('click').on('click', firstClick);
            board.start(true);
            if ($('#loop').is(':checked')) {
                countdownBeforeStartNewGane().then(firstClick);
            }
        });
    }

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

    function checkState() {
        $.get("/stat", function (data) {
            if (data.state === "init") {
                clearInterval(intervalId);
                $('#collectBtn').prop('disabled', true);
                $('#aiBtn').prop('disabled', false);
                $('#turn').html("Click button to start");
                board.start(true);
                $('#aiBtn').click(firstClick);
                $('#collectBtn').click(resetBoard);
            } else if (data.state === "ready") {
                clearInterval(intervalId);
                $('#aiBtn').prop('disabled', false);
                $('#collectBtn').prop('disabled', false);
                board.position(data.fen);
                secondClick();
                $('#collectBtn').click(resetBoard);
            } else if (data.state === "win") {
                clearInterval(intervalId);
                $('#aiBtn').prop('disabled', true);
                $('#collectBtn').prop('disabled', false);
                board.position(data.fen);
                $('#turn').html('Game finished. Reset board.\n');
                $('#collectBtn').click(resetBoard);
            } else {
                $('#collectBtn').prop('disabled', true);
                $('#aiBtn').prop('disabled', true);
                board.position(data.fen);
            }
        });
    }

    var state = $('script[src$="chess1.js"]').attr('state');
    var move = $('script[src$="chess1.js"]').attr('fen');
    console.log(state);
    var boardElement = $('#myBoard');

    var config = {
        position: 'start',
        pieceTheme: 'static/img/chesspieces/wikipedia/{piece}.png',
        draggable: false,
        sparePieces: false,
        position: move
    };
    var board = Chessboard(boardElement, config);
    if (state === "init") {
        $('#collectBtn').prop('disabled', true);
        $('#aiBtn').click(firstClick);
        $('#collectBtn').click(resetBoard);
        board.start(true);
    } else {
        $('#turn').html("Waiting for robot..");
        $('#collectBtn').prop('disabled', true);
        $('#aiBtn').prop('disabled', true);
        var intervalId = setInterval(checkState, 1000);
    }
});
