jQuery(function () {
    function checkState() {
        $.get("/stat", function (data) {
            board.position(data.fen);
        });
    }
    var move = $('script[src$="chess3.js"]').attr('fen');
    var boardElement = $('#myBoard');

    var config = {
        position: 'start',
        pieceTheme: 'static/img/chesspieces/wikipedia/{piece}.png',
        draggable: false,
        sparePieces: false,
        position: move
    };
    var board = Chessboard(boardElement, config);
    setInterval(checkState, 1000)
});
