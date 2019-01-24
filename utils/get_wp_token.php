<?php
$curl = curl_init( 'https://public-api.wordpress.com/oauth2/token' );
curl_setopt( $curl, CURLOPT_POST, true );
curl_setopt( $curl, CURLOPT_POSTFIELDS, array(
    'client_id' => 64348,
    'redirect_uri' => 'http://spirituality.music.blog',
    'client_secret' => 'Lda6YrxyW2O49NsHiPpL2a44z7uTJn3TEp0NafyL8puR8lUFbBuB8dQyy1HN6XBq',
    'code' => 'h6ijUomh6t', // The code from the previous request
    'grant_type' => 'authorization_code'
) );
curl_setopt( $curl, CURLOPT_RETURNTRANSFER, 1);
$auth = curl_exec( $curl );
$secret = json_decode($auth);
var_dump($auth);
$access_key = $secret->access_token;
?>
