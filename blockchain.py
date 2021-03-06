from functools import reduce
import hashlib as hl

import json

# Import two functions from our hash_blockchain.py file. Omit the ".py" in the import
from utility.hash_blockchain import hash_block
from utility.verification import Verification
from block import Block
from transaction import Transaction
from wallet import Wallet

# The reward we give to miners
MINING_REWARD = 10



class Blockchain:
    """The Blockchain class manages the chain of blocks as well as open transactions and the node on which it's running.
    
    Attributes:
        :chain: The list of blocks
        :open_transactions (private): The list of open transactions
        :hosting_node: The connected node (which runs the blockchain).
    """
    def __init__(self, hosting_node_id):
        """The constructor of the Blockchain class."""
        # Our starting block for the blockchain
        genesis_block = Block(0,'',[],100,0)
        # Initializing our (empty) blockchain list
        self.chain = [genesis_block]
        # Unhandled transactions
        self.__open_transaction = []
        self.load_data()
        self.hosting_node = hosting_node_id

    # This turns the chain attribute into a property with a getter (the method below) and a setter (@chain.setter)
    @property
    def chain(self):
        return self.__chain[:]

    # The setter for the chain property
    @chain.setter
    def chain(self,val):
        self.__chain = val

    def get_open_transaction(self):
        return self.__open_transaction[:]

    def load_data(self):
        """Initialize blockchain + open transactions data from a file."""
        try:
            with open('blockchain.txt', mode = 'r') as f:
                # file_content = pickle.loads(f.read())
                # print(file_content)
                file_content = f.readlines()

                # blockchain = file_content['chain']
                # open_transaction = file_content['op']

                blockchain = json.loads(file_content[0][:-1])
                # We need to convert  the loaded data because Transactions should use OrderedDict
                updated_blockchain = []
                for block in blockchain:
                    converted_tx = [Transaction(tx['sender'],tx['recipient'], tx['signature'], tx['amount']) for tx in block['transaction']]
                    updated_block = Block(block['index'] , block['previous_hash'], converted_tx, block['proof'] , block['timestamp'])
    
                    updated_blockchain.append(updated_block)
                self.chain = updated_blockchain
                open_transaction = json.loads(file_content[1])
                # We need to convert  the loaded data because Transactions should use OrderedDict
                updated_transaction = []
                for tx in open_transaction:
                    updated_trans = Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount'])
                    updated_transaction.append(updated_trans)
                self.__open_transaction = updated_transaction
        except (IOError, IndexError):
            pass
        finally:
            print('Cleanup!')


    def save_data(self):
        """Save blockchain + open transactions snapshot to a file."""
        try:
            with open('blockchain.txt', mode = 'w') as f:
                saveable_chain = [block.__dict__ for block in [Block(block_el.index, block_el.previous_hash,[tx.__dict__ for tx in block_el.transaction],block_el.proof, block_el.timestamp) for block_el in self.__chain] ] 
                f.write(json.dumps(saveable_chain))
                f.write('\n')
                saveable_tx = [tx.__dict__ for tx in self.__open_transaction] 
                f.write(json.dumps(saveable_tx))
                # save_data = {
                #     'chain' : blockchain,
                #     'op' : open_transaction
                # }
                # f.write(pickle.dumps(save_data))
        except IOError:
            print('Saving failed!')


    def proof_of_work(self):
        """Generate a proof of work for the open transactions, the hash of the previous block and a random number (which is guessed until it fits)."""  
        last_block = self.__chain[-1]
        last_hash = hash_block(last_block)
        proof = 0
        
        # Try different PoW numbers and return the first valid one
        while not Verification.valid_proof(self.__open_transaction, last_hash, proof):
            proof += 1
        return proof


    def get_balance(self):
        """Calculate and return the balance for a participant."""

        if self.hosting_node == None:
            return None
        participants = self.hosting_node
        # Fetch a list of all sent coin amounts for the given person (empty lists are returned if the person was NOT the sender)
        # This fetches sent amounts of transactions that were already included in blocks of the blockchain
        tx_sender = [[tx.amount for tx in block.transaction if tx.sender == participants] for block in self.__chain]
        # Fetch a list of all sent coin amounts for the given person (empty lists are returned if the person was NOT the sender)
        # This fetches sent amounts of open transactions (to avoid double spending)
        open_tx_sender = [ tx.amount for tx in self.__open_transaction if tx.sender == participants]
        tx_sender.append(open_tx_sender)
        print(tx_sender)
    
        amount_sent = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum + 0, tx_sender, 0)
        # This fetches received coin amounts of transactions that were already included in blocks of the blockchain
        # We ignore open transactions here because you shouldn't be able to spend coins before the transaction was confirmed + included in a block
        tx_recipient = [[tx.amount for tx in block.transaction if tx.recipient == participants] for block in self.__chain]
        print(tx_recipient)
        amount_recieved = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum +  0, tx_recipient, 0)

        #Total balance
        return amount_recieved - amount_sent

    def get_last_blockchain_value(self):
        """Return the last value of the blockchain"""
        if len(self.__chain) < 1:
            return None
        return self.__chain[-1]
            

    # This function accepts two arguments.
    # One required one (transaction_amount) and one optional one (last_transaction)
    # The optional one is optional because it has a default value => [1]

    def add_transaction(self, recipient, sender, signature, amount=1.0):
        """ Append a new value as well as the last blockchain value to the blockchain.
        Arguments:
            sender: The sender of the coins.
            recipient: The recipient of the coins.
            signature: The signature of the transaction.
            amount: The amount of coins sent with the transaction (default = 1.0)
        """
        # transaction = { 'sender': sender,
        #                 'recipient': recipient, 
        #                 'amount': amount
        #               } #dictionaries
        if self.hosting_node == None:
            return False
        transaction = Transaction(sender,recipient, signature, amount)
      
        if Verification.verify_transaction(transaction, self.get_balance):
            self.__open_transaction.append(transaction)    
            self.save_data()
            return True
        return False

    def mine_block(self):
        """Create a new block and add open transactions to it."""
        if self.hosting_node == None:
            return None
        # Fetch the currently last block of the blockchain
        last_block = self.__chain[-1]
        # Hash the last block (=> to be able to compare it to the stored hash value)
        hashed_block = hash_block(last_block)
        proof = self.proof_of_work()
        # Miners should be rewarded, so let's create a reward transaction
        # reward_transaction = {
        #     'sender' : 'MINING',
        #     'recipient': owner,
        #     'amount' : MINING_REWARD
        # }
        reward_transaction = Transaction('MINING',self.hosting_node,'',MINING_REWARD)
        # Copy transaction instead of manipulating the original open_transactions list
        # This ensures that if for some reason the mining should fail, we don't have the reward transaction stored in the open transactions
        copied_transaction = self.__open_transaction[:]
        for tx in copied_transaction:
            if not Wallet.verify_transaction(tx):
                return None
        copied_transaction.append(reward_transaction)
        block = Block(len(self.__chain), hashed_block, copied_transaction , proof)
        
    
        self.__chain.append(block)
        self.__open_transaction = []
        self.save_data()
    
        return block






