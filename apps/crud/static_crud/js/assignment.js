// document.addEventListener('DOMContentLoaded', function() {
//     var assignButton = document.getElementById('assignButton');
//     assignButton.addEventListener('click', function() {
//         var url = this.getAttribute('data-url');
//         window.location.href = url;
//     });
// });


// function toggleAssignButton() {
//     var title = document.getElementById('title').value.trim();
//     var postContent = document.getElementById('postContent').value.trim();
//     var assignButton = document.getElementById('assignButton');
//     // タイトルと課題詳細の両方にテキストが入力されているかをチェック
//     if (title && postContent) {
//         assignButton.disabled = false; // ボタンを有効にする
//     } else {
//         assignButton.disabled = true; // ボタンを無効にし、グレーアウトする
//     }
// }

// DOMContentLoaded イベントを待ってからイベントハンドラを設定する
document.addEventListener('DOMContentLoaded', function () {
// ファイル入力フィールドにイベントリスナーを追加
document.getElementById('fileUpload').addEventListener('change', function (e) {
    var file = e.target.files[0];
    var reader = new FileReader();
    // ファイルの読み込みが完了したら実行される
    reader.onload = function(e) {
        var imgSrc = e.target.result; // 画像のBase64データ
        // 新しいカードのHTMLを生成
        var cardHtml = `
        <div class="card added-card">
            <div class="row no-gutters">
                <div class="col-md-3">
                    <img src="${imgSrc}" class="card-img card-img-small" alt="アップロードされた画像">
                </div>
                <div class="col-md-7">
                    <div class="card-body">
                        <p class="card-text">${file.name}</p>
                    </div>
                </div>
                <div class="col-md-2">
                    <button class="btn btn-link text-right remove-card-btn">
                        <i class="fas fa-times-circle"></i>
                    </button>
                </div>
            </div>
        </div>`;
            // テキストエリアの下にカードを追加
            document.getElementById('postContent').insertAdjacentHTML('afterend', cardHtml);

            // 削除ボタンのクリックイベントを設定
            document.querySelectorAll('.remove-card-btn').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    this.parentElement.parentElement.parentElement.remove(); // カードを削除
                });
            });
        };

        // ファイルの読み込みを開始
        reader.readAsDataURL(file);
    });
});

