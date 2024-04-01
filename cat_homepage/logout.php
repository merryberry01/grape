<!-- logout.php -->

<h1>logout...</h1>

<?php
setcookie('user', '', time() - 3600);

header("Location: index.php");
exit();
?>
