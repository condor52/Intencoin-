const bip39 = require('bip39');
const { BIP32Factory } = require('bip32');
const ecc = require('tiny-secp256k1');
const bip32 = BIP32Factory(ecc);
const bitcoin = require('bitcoinjs-lib');

function networkForIntencoin() {
  return bitcoin.networks.bitcoin;
}

function seedToRoot(mnemonic) {
  if (!mnemonic) throw new Error('ADMIN_WALLET_SEED missing');
  const seed = bip39.mnemonicToSeedSync(mnemonic);
  return bip32.fromSeed(seed, networkForIntencoin());
}

function deriveAddress(mnemonic, account = 0, change = 0, index = 0) {
  const root = seedToRoot(mnemonic);
  const path = `m/44'/0'/${account}'/${change}/${index}`;
  const node = root.derivePath(path);
  const pay = bitcoin.payments.p2pkh({
    pubkey: Buffer.from(node.publicKey),
    network: networkForIntencoin()
  });
  return { path, address: pay.address, wif: node.toWIF() };
}

module.exports = { deriveAddress };





0

