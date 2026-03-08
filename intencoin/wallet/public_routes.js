const db = require('./db');

module.exports = function(app){
  // GET /public/balance?address=1NFuTx...
  app.get('/public/balance', (req,res)=>{
    try{
      const address = String(req.query.address||'').trim();
      if(!address) return res.status(400).json({error:'address required'});

      // buscar por chain_addresses (direcciones generadas) o por wallets.deposit_address
      let row = db.prepare(
        'SELECT user_id FROM chain_addresses WHERE address=? ORDER BY created_at DESC LIMIT 1'
      ).get(address);

      if(!row){
        row = db.prepare(
          'SELECT user_id FROM wallets WHERE deposit_address=? LIMIT 1'
        ).get(address);
      }

      if(!row) return res.status(404).json({error:'address not found'});

      const u = db.prepare(
        'SELECT account_no, balance FROM users WHERE id=?'
      ).get(row.user_id);

      if(!u) return res.status(404).json({error:'user not found'});

      return res.json({ address, account_no: u.account_no, balance: u.balance });
    }catch(e){
      return res.status(500).json({error:e.message});
    }
  });
};
