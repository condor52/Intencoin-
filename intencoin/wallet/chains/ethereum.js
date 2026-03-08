const { ethers } = require('ethers');

function ethAdminWallet(){
  const rpc = process.env.ETH_RPC_URL;
  const pk  = process.env.ETH_ADMIN_PK;
  if(!rpc || !pk) throw new Error('ETH_RPC_URL / ETH_ADMIN_PK missing');
  const provider = new ethers.JsonRpcProvider(rpc);
  const wallet = new ethers.Wallet(pk, provider);
  return wallet;
}

async function getEthAddress(){
  const w = ethAdminWallet();
  return await w.getAddress();
}

async function sendEth(to, amountEth){
  const w = ethAdminWallet();
  const tx = await w.sendTransaction({ to, value: ethers.parseEther(String(amountEth)) });
  return tx.hash;
}

module.exports = { getEthAddress, sendEth };
