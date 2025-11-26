function validateCrypto() {
    let selectedCrypto = document.forms["cryptoForm"]["selected_crypto"].value;
    let address = document.forms["cryptoForm"]["new_address"].value;
    var isValid;
    if (selectedCrypto == "Bitcoin") {
        isValid = validateBitCoin(address);
    } else if (selectedCrypto == "Ethereum") {
        isValid = validateEthereum(address);
    } else if (selectedCrypto == "BitcoinCash") {
        isValid = validateBCH(address)
    } else {
        $.notify("Select a Crypto to Continue!", {
            style: "custom",
            className: "danger"
        });
    }
    if (!isValid) {
        $.notify("Enter a valid Crypto Address!", {
            style: "custom",
            className: "danger"
        });
    }
    return isValid;
}

function validateBCH(address) {
    /*** 
     * Params: BCH Address
     * ***/
    if (address == null || address == "" || address == " ") {
        return "empty";
    }
    if (address.startsWith("bitcoincash:")) {
        address = address.slice(12);
    }
    let regex = new RegExp(/^[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{42}$/);

    if (!regex.test(address) == true) {
        return false;
    }
    return true;
}


function validateEthereum(address) {
    /*** 
    * Params: Ethereum Address
    * ***/

    let regex = new RegExp(/^(0x)?[0-9a-fA-F]{40}$/);

    if (address == null || address == "" || address == " ") {
        return "empty";
    } else if (regex.test(address) == true) {
        return true;
    } else {
        return false;
    }

}

function validateBitCoin(address) {
    /*** 
     * Params: BitCoin Address
     * ***/
    let regex = new RegExp(/^(bc1|[13])[a-km-zA-HJ-NP-Z1-9]{25,34}$/);
    if (address == null || address == "" || address == " ") {
        return "empty";
    } else if (regex.test(address) == true) {
        return true;
    } else {
        return false;
    }
}

// async function CryptoEditForm(crypto, selected_c) {
//     if(selected_c == "BTC"){
//         selected_c = "Bitcoin"
//         var isValidAddress = validateBitCoin(crypto);
//     }else if(selected_c == "BCH"){
//         selected_c = "BitcoinCash"
//         var isValidAddress = validateBCH(crypto);
//     }else if(selected_c == "ETH"){
//         selected_c = "Ethereum"
//         var isValidAddress = validateEthereum(crypto);
//     }else{
//         $.notify("Please select a Crypto Address", {
//             style: "custom",
//             className: "danger"
//         });
//         return;
//     }
//     if(isValidAddress == true){
//         const data = {
//             selected_crypto: selected_c,
//             new_address: crypto
//           };          
//         const request = await fetch("/update_bch_address/", {
//             method: 'POST',
//             headers: {
//                 "Content-Type": "application/json"
//             },
//             body: JSON.stringify(data),
//         });
//         if(request.status == 200){
//             window.location.reload();
//         }
//     }else{
//         $.notify("Please enter a valid Crypto Address", {
//             style: "custom",
//             className: "danger"
//         });
//     }
// }
// TEST THE VALIDATORS
// BitCoin VALIDATOR
// Uncomment the below code

// var btc = [
//     '1BoatSLRHtKNngkdXEeobR76b53LETtpyT',
//     '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
//     '2QLbGuc3GWptSpWLKwJfaV8z6Z1k7ydfGr',
//     '1PeChKY22Zq8Kipj6nKzf8xVRmXo5q3Ne',
//     '1dice8EMZmqKvrGE4Qc9bUFf9PX3xaYDp',
//     'ACounterpartyXXXXXXXXXXXXXXXUWLpVr',
//     '3ELzJkt9A1sp8ysTTz9TnL5KszYQmBpdr5',
//     'aBitcoinEaterAddressDontSendf59kuE',
//     '1Dorian4RoXcnBv9hnQ4Y2C1an6NJ4UrjX',
//     '1AGRx1kJhx8ZgB4jQDL3Ka5Mf9xSKYtL2p',
//     '1GDbUgo6X2i29K1jZ4WDEz6qczdVqzK7oa',
//     '1MZ8Rjkt8Tgk5n98dRwj29s5LZY2zp8mcK',
//     '1HoDW3sJv5X4xmtPvknm78X3pYYUGTkJK ',
//     '1AE1LoNUouPjqaAcdRFLednhrHiDRJX6W3',
//     '1FfmbHfnpaZjKFvyi1okTjJJusN455paPH',
//     '1HCKjUpRGcrrRAtFaaCAUaGjsPx9oYmLaZ',
//     '1L8meqhHjBckTnCvFkg1aeDdWxqa5i5a8n',
//     '1ice7DUtRURKToyD8fX4abRekiYnoVHTa',
//     '1dice8EMZmqKvrGE4Qc9bUFf9PX3xaYDp ',
//     '1Ch5cMc8s8QzCx9vjvcu6zG8gTNDzYf9ZT',
// ]
// for(var i=0; i<btc.length; i++){
//     validateBitCoin(btc[i])
// }

// BCH VALIDATOR:

// const bch = [
//     'bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a', // valid
//     'bitcoincash:invalidaddress', // invalid
//     'bitcoincash:qr95d8m1u9uqzkhfupzr7a92yt2ftmqh69z38rfd6u', // valid
//     'bitcoincash:qqjqsy0uqwcjseaynv78k34tpyn59zykwscx8rfw4d', // valid
//     'invalid-bch-address', // invalid
//     'bitcoincash:qz83apuhmqtqlq86fn0x6yq7vqxd4lk80t4p70f4n3', // valid
//     'bitcoincash:qz97ad85zffn3dyfxaqnczlgv02xw5qh0mrxy8j0kh', // valid
//     'bitcoincash:qr7h9v4rgj2ldqh8cmtk8c46n32f7r6w4u0h3u4ff4', // valid
//     'bitcoincash:wrongaddressformathere', // invalid
//     'bitcoincash:qrlm6j6h8m3phfr62wymvjjsyqf3jqlmejsh5dxz38' // valid
// ];

// for(var i=0; i<bch.length; i++){
//     validateBCH(bch[i])
// }

// Ethereum validator 

// const ethAddresses = [
//     '0x742d35Cc6634C0532925a3b844Bc454e4438f44e', // valid
//     '0x281055afc982d96fabbc85ea68f7f1239a0f8c78', // valid
//     'invalidethaddress', // invalid
//     '0x6f46cf5569aefa1acc1009290c8e043747172d89', // valid
//     '0x66f820a414680b5bcda5eeca5dea238543f42054', // valid
//     '0xdc76cd25977e0a5ae17155770273ad58648900d3', // valid
//     '0x53d284357ec70ce289d6d64134dfac8e511c8a3d', // valid
//     '0xfe9e8709d3215310075d67e3ed32a380ccf451c8', // valid
//     '0xnotanethereumaddress00000000000000000000', // invalid
//     '0x742d35cc6634c0532925a3b844bc454e4438f44e', // valid
//     '0xfe7b67929579b87a38c1c77661d9f258a4015f9e', // valid
//     '0x742d35Cc6634C0532925A3b844Bc764E4438f44e' // valid
// ];

// for(var i=0; i<ethAddresses.length; i++){
//     validateEthereum(ethAddresses[i])
// }
