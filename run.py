# flask modules 
from flask import Flask, redirect, url_for, request, \
render_template, make_response, session, abort, flash
import json

# object_id(쿼리에 있는 _id의 자료형 변환)
from bson.objectid import ObjectId

# set session time 
from datetime import timedelta
from datetime import datetime
import time 

# file module
from werkzeug.utils import secure_filename 

# pymongo
import pymongo 
from pymongo import MongoClient

import certifi

# Connect to MongoDB Cluster
cluster = MongoClient("mongodb+srv://admin:dgu5005@cluster0.rmhq5as.mongodb.net/?retryWrites=true&w=majority",
                      tlsCAFile=certifi.where())
db = cluster["Software_Engineering_Coin_Market"]

# "app"을 통해 Flask에 연결
app = Flask(__name__)

# # flash(경고 문구)를 사용하기 위해서 설정
app.config["SECRET_KEY"] = "Software_Engineering_Coin_Market"

# session의 지속시간을 설정 
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

# UTC시간을 바꿔주기 위함
@app.template_filter("utc_time")
def format_utctime(val) :
    if val is None :
        return ""
    
    now_timestamp = time.time() # 클라이언트의 시간 
    offset = datetime.fromtimestamp(now_timestamp)- datetime.utcfromtimestamp(now_timestamp)

    val = datetime.fromtimestamp((int(val)/1000)) + offset 

    return val.strftime("%Y-%m-%d %H:%M:%S")
    

## 마켓에서 처음에 코인 100개를 넣어두는 코드
## 마켓의 처음 코인 개수를 100개로 다시 돌리는 거

# marketplace = db["MarketPlace"]
# result = {
#     "market_coin_id" : 'MASTER_juho',
#     "cur_coin_amount" : 100, # 현재 코인의 개수
#     "cur_coin_price" : 100 # 현재 코인의 가격
# }
# marketplace.insert_one(result)

# marketplace.update_one({"market_coin_id" : "MASTER_juho"}, {"$set" : {
#     "cur_coin_amount" : 100 
# }})


## 사용자의 코인개수를 0개로 바꿔주는 코드
member = db["Account_DB"]
member.update_one({'member_id' : 'qwer'}, {"$set" : {
    "coin_amount" : 0,
    "cash_amount" : 0
}})


# 첫 화면 [홈페이지] -> 시작점
@app.route('/', methods=["GET", "POST"])
def homepage() :
    if request.method == "GET" :
        # 코인가격의 흐름을 알아보기 위함
        coin_price_flow = db["Coin_Price_Flow"]
        datas = list(coin_price_flow.find({})) # 전체 데이터베이스를 다 가져옴
        dataList = []
        for item in datas:
            del item['_id']
        for item in datas:
            dataList.append(json.dumps(item))
        print(dataList)

        # 홈페이지의 코인 개수와 코인 가격을 알기 위함
        marketplace = db["MarketPlace"]
        market_cur_coin = marketplace.find_one({"market_coin_id" : 'MASTER_juho'})

        # 사용자의 session이 있을 때 코인과 현금의 양을 알기 위함
        if session.get("member_id") :
            Account = db["Account_DB"]
            user_info = Account.find_one({"member_id" : session.get("member_id")})
            return render_template('Coin_Market_Homepage.html', market_cur_coin=market_cur_coin, user_info=user_info, datas=datas)

        return render_template('Coin_Market_Homepage.html', market_cur_coin=market_cur_coin, datas=datas)

    elif request.method == "POST" :
        # 코인가격의 흐름을 알아보기 위함
        coin_price_flow = db["Coin_Price_Flow"]
        datas = coin_price_flow.find({}) # 전체 데이터베이스를 다 가져옴

        # 홈페이지의 코인 개수와 코인 가격을 알기 위함
        marketplace = db["MarketPlace"]
        market_cur_coin = marketplace.find_one({"market_coin_id" : 'MASTER_juho'})

        # 사용자의 session이 있을 때 코인과 현금의 양을 알기 위함
        if session.get("member_id") :
            Account = db["Account_DB"]
            user_info = Account.find_one({"member_id" : session.get("member_id")})

        deposit_amount = request.form['deposit_amount']
        withdraw_amount = request.form['withdraw_amount']

        is_plus = False # 입금하는 경우 
        is_minus = False # 출금하는 경우

        if deposit_amount == "" and withdraw_amount == "" : # 금액을 기입하지 않은 경우
            flash("금액을 입력하지 않았습니다.")
            return redirect(url_for('homepage'))

        if deposit_amount == "" :
            is_minus = True 
            withdraw_amount = int(withdraw_amount)
        else :
            is_plus = True 
            deposit_amount = int(deposit_amount)
        
        Account = db["Account_DB"]
        user_info = Account.find_one({"member_id" : session.get("member_id")})

        prev_cash = user_info["cash_amount"]
                  
        if is_plus : 
            ADD = prev_cash + deposit_amount
            Account.update_one({"member_id" : session.get("member_id")}, {"$set" : {"cash_amount" : ADD
                }})
        else :
            MINUS = prev_cash - withdraw_amount

            if MINUS < 0 :
                flash(f"출금하고 싶은 금액보다 {-MINUS}원 보유한 금액이 적습니다.")
                return redirect(url_for('homepage'))
            Account.update_one({"member_id" : session.get("member_id")}, {"$set" : {
                "cash_amount" : MINUS
            }})

        return redirect(url_for('homepage'))


# 마켓에서 코인을 사고 팔 때
@app.route('/coin_trade_market', methods=["GET", "POST"])
def coin_trade_market() :
    # 로그인이 안됐을 때 경고문과 함께 홈페이지로 돌아가게 만들어줌
    if session.get("member_id") is None :
        flash("로그인을 해야 마켓과 코인거래를 할 수 있습니다.")
        return redirect(url_for('homepage'))

    # 홈페이지의 코인 개수와 코인 가격을 알기 위함
    marketplace = db["MarketPlace"]
    market_cur_coin = marketplace.find_one({"market_coin_id" : 'MASTER_juho'})


    # 사용자의 정보를 이용하기 위함
    Account = db["Account_DB"]
    user_info = Account.find_one({"member_id" : session.get("member_id")})

    # 코인가격의 흐름을 알아보기 위함
    coin_price_flow = db["Coin_Price_Flow"]


    if request.method == "POST" :
        want_coin_amount = request.form.get("buy_coin_amount")

        # 빈칸을 입력한 경우
        if want_coin_amount == "" :
            flash("아무것도 입력하지 않았습니다. 구매하고 싶은 코인의 개수를 입력해주세요.")
            return redirect(url_for('homepage'))
        
        # 문자를 입력한 경우
        if not want_coin_amount.isdigit() :
            flash("문자를 입력했습니다. 구매하고 싶은 코인의 개수를 입력해주세요.")
            return redirect(url_for('homepage'))


        # 사용자가 구매하고 싶은 코인이 마켓이 보유한 코인의 개수보다 많을 때
        if int(want_coin_amount) > market_cur_coin["cur_coin_amount"] : 
            flash("마켓이 보유한 코인의 개수보다 더 많이 선택하셨습니다.")
            return redirect(url_for('homepage'))
        
        # 사용자가 보유한 돈을 초과하는 경우

        x = int(want_coin_amount) # 구매하고 싶은 코인 개수

        a = market_cur_coin["cur_coin_amount"] # 마켓이 들고 있는 코인 개수
        b = market_cur_coin["cur_coin_price"] # 현재 코인의 시세[가격]


        c = user_info["cash_amount"] # 사용자가 가지고 있는 돈(원) 액수
        d = user_info["coin_amount"] # 사용자가 가지고 있는 코인 개수

        need_cash = x * b
        have_cash = c
        diff = have_cash - need_cash

        if diff < 0 :
            flash(f"보유한 돈보다 {-diff}원이 더 필요합니다 ")
            return redirect(url_for('homepage'))
        
        else :
            # 사용자의 코인과 현금의 개수 변동
            Account.update_one({"member_id" : session.get("member_id")}, {"$set" : {
                "coin_amount" : d+x,
                "cash_amount" : diff
            }})

            # 마켓의 코인의 개수 변동
            marketplace.update_one({"market_coin_id" : 'MASTER_juho'}, {"$set" : {
                "cur_coin_amount" : a-x
            }})

            flash(f"코인 {x}개를 {need_cash}원에 구매했고 {diff}원 남았습니다.")


            cur_utc_time = round(datetime.utcnow().timestamp() * 1000)
            
            result = {
                "buy_id" : session.get("member_id"), # 코인을 산 id
                "sell_id" : "marketplace", # 코인을 판 id (여기선 마켓플레이스)
                "trade_amount" : x, # 코인 거래 개수
                "trade_price" : b, # 코인 거래 가격
                "trade_time" : cur_utc_time # 코인 거래 시간
            }

            coin_price_flow.insert_one(result)
            return redirect(url_for('homepage'))


    if session.get("member_id") :
        return render_template('Coin_Trade_Market.html', market_cur_coin=market_cur_coin, user_info=user_info)




# 회원가입 페이지
@app.route('/sign_up_member', methods=["GET", "POST"])
def sign_up_member() :
    if session.get("member_id") : # 로그인이 된 상황일 때
        flash("이미 로그인 된 상태입니다!")
        return redirect(url_for("homepage"))

    if request.method == "POST" :
        member_id = request.form.get("sign_up_id", type=str)
        member_pw = request.form.get("sign_up_pw", type=str)

        if member_id == "" : 
            flash("아이디를 입력하지 않았습니다.")
            return render_template("Sign_Up_Member.html")
        elif member_pw == "" :
            flash("비밀번호를 입력하지 않았습니다.")
            return render_template("Sign_Up_Member.html")

        Accounts = db["Account_DB"]
        print('여기')
        member_num = Accounts.count_documents({"member_id" : member_id})
        print(member_num)
        if member_num > 0 :
            flash("이미 존재하는 아이디입니다.")
            return render_template("Sign_Up_Member.html")
        
        result = {
            "member_id" : member_id,
            "member_pw" : member_pw,
            "coin_amount" : 0, # 갖고있는 코인 갯수를 0으로 
            "cash_amount" : 0  # 갖고있는 현금을 0으로
        }
        
        Accounts.insert_one(result)
        flash("회원가입이 완료됐습니다.")
        return redirect(url_for("sign_in_member"))
    
    else :
        return render_template("Sign_Up_Member.html")


# 로그인 페이지 
@app.route('/sign_in_member', methods=["GET", "POST"])
def sign_in_member() :
    if session.get("member_id") : # 로그인이 된 상황일 때
        flash("이미 로그인 된 상태입니다!")
        return redirect(url_for("homepage"))

    if request.method == "POST" :
        member_id = request.form.get("sign_in_id")
        member_pw = request.form.get("sign_in_pw")

        Accounts = db["Account_DB"]
        print("여기")
        data = Accounts.find_one({"member_id" : member_id})
        print(data)
        if data is None :
            flash("가입되지 않은 회원정보입니다.")
            return redirect(url_for("sign_in_member"))
        
        else :
            if data.get("member_pw") == member_pw :
                session["member_id"] = member_id 
                session.permanent = True 
                flash("로그인에 성공했습니다!")
                return redirect(url_for('homepage'))
            else :
                flash("비밀번호가 일치하지 않습니다.")
                return redirect(url_for("sign_in_member"))  
                      
    else :
        return render_template("Sign_In_Member.html")


# 로그아웃
@app.route('/sign_out_member')
def sign_out_member() :
    # 로그인이 안됐을 때
    if session.get("member_id") is None :
        flash("로그인을 한 적이 없습니다.")
        return redirect(url_for('sign_in_member'))

    session.pop('member_id')
    flash("로그아웃 됐습니다.")
    return redirect(url_for('sign_in_member'))


# 코인 판매 게시판
@app.route('/coin_sale_list')
def coin_sale_list() :
    # 로그인이 안됐을 때 경고문과 함께 홈페이지로 돌아가게 만들어줌
    if session.get("member_id") is None :
        flash("로그인을 해야 판매 게시판에 들어갈 수 있습니다.")
        return redirect(url_for('homepage'))
    
    # 판매글들을 다 보기 위함
    Sale_Post = db["Sale_Post_DB"]
    datas = Sale_Post.find({}) # 전체 데이터베이스를 다 가져옴

    # 사용자의 정보를 이용하기 위함
    Account = db["Account_DB"]
    user_info = Account.find_one({"member_id" : session.get("member_id")})

    return render_template('Coin_Trade_list.html', datas=list(datas), user_info=user_info)


# 코인 판매 게시글 올리기
@app.route('/write_coin_sale_post', methods=["GET", "POST"])
def write_coin_sale_post() :
    # 로그인이 안됐을 때 경고문과 함께 홈페이지로 돌아가게 만들어줌
    if session.get("member_id") is None :
        flash("로그인을 해야 판매 글을 작성할 수 있습니다.")
        return redirect(url_for('homepage'))
    
    # 고객의 정보를 이용하기 위함
    Account = db["Account_DB"]
    user_info = Account.find_one({"member_id" : session.get("member_id")})

    # 홈페이지의 코인 개수와 코인 가격을 알기 위함
    marketplace = db["MarketPlace"]
    market_cur_coin = marketplace.find_one({"market_coin_id" : 'MASTER_juho'})


    # POST인 경우
    if request.method == "POST" :
        sale_post_writer = request.form.get("sale_post_writer") # 판매자 아이디
        sale_post_title = request.form.get("sale_post_title") # 판매 글 제목
        sale_post_coin_amount = request.form.get("sale_post_coin_amount") # 판매 코인 개수
        sale_post_coin_price = request.form.get("sale_post_coin_price") # 판매 코인 가격 

        # 만약 보유한 코인 보다 많은 코인을 파려고 게시글을 작성했을 때
        if user_info["coin_amount"] < int(sale_post_coin_amount) :
            flash("보유한 코인의 양보다 많은 양을 파려고 합니다!")
            return redirect('write_coin_sale_post')

        sale_post_datas = {
            "sale_post_writer" : sale_post_writer,
            "sale_post_title" : sale_post_title,
            "sale_post_coin_amount" : sale_post_coin_amount,
            "sale_post_coin_price" : sale_post_coin_price
        }

        # Database 중 "Sale_Post_DB" 칼럼 선택
        Sale_Post = db["Sale_Post_DB"]

        # "Sale_Post_DB"에 데이터 입력
        x = Sale_Post.insert_one(sale_post_datas)
        
        return redirect(url_for('coin_sale_list'))
        # return redirect(url_for("view_own_coin_sale_post", own_id=x.inserted_id))

    # GET인 경우
    else :
        return render_template('Write_Coin_Sale_Post.html', user_info=user_info, market_cur_coin=market_cur_coin)


# 코인 판매 글이 조건에 부합하는가 판단 후 적었던 내용들을 표시
# 조건에 부합하지 않는다면 오류 메세지 후 작성칸으로 다시 가기
@app.route('/view_own_coin_sale_post/<own_id>') 
def view_own_coin_sale_post(own_id) :
    if own_id is not None :
        Sale_Post = db["Sale_Post_DB"]
        data = Sale_Post.find_one({"_id" : ObjectId(own_id)})

        if data is not None :
            need_money = int(data.get("sale_post_coin_amount")) * int(data.get("sale_post_coin_price"))
            result = {
                "sale_post_own_id" : data.get("_id"),
                "sale_post_writer" : data.get("sale_post_writer"),
                "sale_post_title" : data.get("sale_post_title"),
                "sale_post_coin_amount" : int(data.get("sale_post_coin_amount")),
                "sale_post_coin_price" : data.get("sale_post_coin_price"),
                "need_money" : need_money
            }
            # 홈페이지의 코인 개수와 코인 가격을 알기 위함
            marketplace = db["MarketPlace"]
            market_cur_coin = marketplace.find_one({"market_coin_id" : 'MASTER_juho'})

            # 사용자의 정보를 이용하기 위함
            Account = db["Account_DB"]
            user_info = Account.find_one({"member_id" : session.get("member_id")})
            
            return render_template("View_Own_Coin_Sale_Post.html",result=result, user_info=user_info, market_cur_coin=market_cur_coin)
    return abort(404)


# 코인 거래가 끝나고 해당 판매 게시글을 삭제 하고
# 사용자와 판매자 간의 코인의 수, 남은 돈의 액수를 변경
@app.route('/delete_data_change/<seller_own_id>')
def delete_data_change(seller_own_id) :
    sale_post_DB = db["Sale_Post_DB"]
    data = sale_post_DB.find_one({"_id" : ObjectId(seller_own_id)}) # 판매자 글의 정보를 받아옴
    
    seller = data["sale_post_writer"] # 판매자의 아이디
    seller_minus_coin = data["sale_post_coin_amount"] # 판매자가 코인을 팔아서 줄어들 코인 개수
    seller_plus_coin = data["sale_post_coin_price"] # 판매자가 코인을 팔아서 늘어날 돈의 개수

    # 판매자가 판 코인의 개수만큼 판매자의 코인 개수를 줄여줌
    account_DB = db["Account_DB"]
    member = account_DB.find_one({"member_id" : seller})

    # 1) 코인 개수 감소
    x = int(member["coin_amount"]) - int(data["sale_post_coin_amount"])

    # 2) 잔액의 증가
    y = int(member["cash_amount"]) + (int(data["sale_post_coin_price"]) * int(data["sale_post_coin_amount"]))

    # 1,2 번을 실제 DB에 적용시켜줌
    account_DB.update_one({"member_id" : seller}, {"$set" : {
        "coin_amount" : x,
        "cash_amount" : y
    }})

    # 구매자의 정보도 수정해야함
    buyer_id = session.get("member_id")
    buyer = account_DB.find_one({'member_id' : buyer_id})

    # 1) 코인 개수 증가
    q = int(buyer["coin_amount"]) + int(data["sale_post_coin_amount"])
    # 2) 잔액의 감소
    w = int(buyer["cash_amount"]) - (int(data["sale_post_coin_price"]) * int(data["sale_post_coin_amount"]))

    account_DB.update_many({"member_id" : buyer_id}, {"$set" : {
        "coin_amount" : q,
        "cash_amount" : w
    }})


    # 그리고, 거래일지DB에도 추가시켜준다.
    coin_price_flow = db["Coin_Price_Flow"]
    cur_utc_time = round(datetime.utcnow().timestamp() * 1000) # utc 시간을 위함
    result = {
        "buy_id" : buyer_id, # 코인을 산 id
        "sell_id" : seller, # 코인을 판 id (여기선 마켓플레이스)
        "trade_amount" : int(data["sale_post_coin_amount"]), # 코인 거래 개수
        "trade_price" : int(data["sale_post_coin_price"]), # 코인 거래 가격
        "trade_time" : cur_utc_time # 코인 거래 시간
    }
    coin_price_flow.insert_one(result)

    # 현재 코인의 시세또한 바꿔준다.
    marketplace = db["MarketPlace"]
    marketplace.update_one({"market_coin_id" : "MASTER_juho"}, {"$set" : {
        "cur_coin_price" : int(data["sale_post_coin_price"]) 
    }})

    # 그리고, 판매 글도 거래됐으므로 지워준다.
    flash("거래가 완료됐습니다!")
    sale_post_DB.delete_one({"sale_post_writer" : seller})

    return redirect(url_for('homepage'))


# Main code
if __name__ == "__main__" :
    app.run(host="0.0.0.0", port=8000, debug=True)