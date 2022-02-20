/*
Recipient app structure
*/
var recipientItems = [];

class RecipientList extends React.Component {
  render () {
    var items = this.props.items.map((item, index) => {
      return (
        <RecipientListItem key={index} item={item} index={index} removeItem={this.props.removeItem}/>
      );
    });
    return (
      <ul className="list-group"> {items} </ul>
    );
  }
}

class RecipientListItem extends React.Component {
  constructor(props) {
    super(props);
    this.onClickClose = this.onClickClose.bind(this);
  }
  onClickClose() {
    var index = parseInt(this.props.index);
    this.props.removeItem(index);
  }
  render () {
    var recipientClass = "undone"
    return(
      <li className="list-group-item ">
        <div className={recipientClass}>
          {this.props.item.value.newAddressValue} --- {this.props.item.value.newAmountValue}
          <button type="button" className="close" onClick={this.onClickClose}>&times;</button>
        </div>
      </li>
    );
  }
}

class RecipientForm extends React.Component {
  constructor(props) {
    super(props);
    this.onSubmit = this.onSubmit.bind(this);
  }
  componentDidMount() {
    this.refs.address.focus();
    this.refs.amount.focus();
  }
  onSubmit(event) {
    event.preventDefault();
    var newAddressValue = this.refs.address.value;
    var newAmountValue = this.refs.amount.value;

    if(newAddressValue) {
      console.log(newAddressValue);
      this.props.addItem({newAddressValue, newAmountValue});
      this.refs.form.reset();
    }
  }
  render () {
    return (
      <form ref="form" onSubmit={this.onSubmit} className="form-inline">
        <input type="text" ref="address" className="form-control" placeholder="add a testnet address..."/>
        <input type="text" ref="amount" className="form-control" placeholder="amount in ada"/>
        <button type="submit" className="btn btn-default">Add</button>
      </form>
    );
  }
}

class RecipientHeader extends React.Component {
  render () {
    return <h1>Recipient list</h1>;
  }
}

class RecipientApp extends React.Component {
  constructor (props) {
    super(props);
    this.onChange = this.onChange.bind(this);
    this.addItem = this.addItem.bind(this);
    this.removeItem = this.removeItem.bind(this);
    this.submitRequest = this.submitRequest.bind(this);
    this.prepare_sender = this.prepare_sender.bind(this);
    this.connectWallet = this.connectWallet.bind(this);
    this.signTx = this.signTx.bind(this);
    this.sendTxAndWitnessBack = this.sendTxAndWitnessBack.bind(this);
    this.state = {
      recipientItems: recipientItems,
      connected: false
    };
    window.cardano.nami.isEnabled().then(
      (enabled) => {
          this.setState({connected: enabled})
      }
    )
  }
  onChange(e) {

  }
  addItem(recipientItem) {
    recipientItems.push({
      index: recipientItems.length+1,
      value: recipientItem,
    });
    this.setState({recipientItems: recipientItems});
  }
  removeItem (itemIndex) {
    recipientItems.splice(itemIndex, 1);
    this.setState({recipientItems: recipientItems});
  }

  submitRequest(senders, change_address) {
    console.log(senders);
    console.log(change_address);
    console.log(this.state.recipientItems);
    fetch('build_tx', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(
        {
          'senders': senders,
          'change_address': change_address,
          'recipients': this.state.recipientItems.map((item, index) => {
            return [item.value.newAddressValue, item.value.newAmountValue]
          })
        }
      )
    })
    .then(response => response.json())
    .then(this.signTx)
  }

  signTx(tx) {
    console.log(tx);
    window.cardano.signTx(tx['tx']).then((witness) => {
      this.sendTxAndWitnessBack(tx['tx'], witness)
    })
  }

  sendTxAndWitnessBack(tx, witness) {
    console.log(witness)
    fetch('submit_tx', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(
        {
          'tx': tx,
          'witness': witness
        }
      )
    })
    .then(response => response.json())
    .then(data => {
        alert("Transaction: " + data["tx_id"] + " submitted!");
    })
  }

  prepare_sender() {
    window.cardano.getUsedAddresses().then((senders) => {
        window.cardano.getChangeAddress().then((change_address) => {
            this.submitRequest(senders, change_address);
        })
    })
  }

  connectWallet(event) {
    if (!this.state.connected) {
      window.cardano.nami.enable().then(
        () => {
          this.setState({connected: true})
        }
      );
    }
  }
  render() {
    return (
      <div id="main">
        <RecipientHeader />
        <RecipientList items={this.props.initItems} removeItem={this.removeItem}/>
        <RecipientForm addItem={this.addItem} />
        <br/>
        <button disabled={!this.state.connected} onChange={this.onChange} onClick={this.prepare_sender}>Submit Tx</button>
        <button disabled={this.state.connected} onChange={this.onChange} onClick={this.connectWallet}>Connect Nami wallet</button>
      </div>
    );
  }
}

ReactDOM.render(<RecipientApp initItems={recipientItems}/>, document.getElementById('app'));

