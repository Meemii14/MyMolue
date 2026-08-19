import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from services.location import haversine_km

BASE_DIR=os.path.abspath(os.path.dirname(__file__))
db=SQLAlchemy(); bcrypt=Bcrypt(); login_manager=LoginManager(); login_manager.login_view='login'
class User(UserMixin,db.Model):
 id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(120),nullable=False); email=db.Column(db.String(150),unique=True,nullable=False); phone=db.Column(db.String(30),unique=True,nullable=False); password_hash=db.Column(db.String(255),nullable=False); role=db.Column(db.String(20),nullable=False,default='rider'); is_online=db.Column(db.Boolean,default=False,nullable=False); latitude=db.Column(db.Float); longitude=db.Column(db.Float); created_at=db.Column(db.DateTime,default=datetime.utcnow)
 rides_as_rider=db.relationship('Ride',foreign_keys='Ride.rider_id',backref='rider',lazy=True); rides_as_driver=db.relationship('Ride',foreign_keys='Ride.driver_id',backref='driver',lazy=True); offers=db.relationship('RideOffer',backref='driver',lazy=True,cascade='all, delete-orphan')
class Ride(db.Model):
 id=db.Column(db.Integer,primary_key=True); rider_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); driver_id=db.Column(db.Integer,db.ForeignKey('user.id')); pickup=db.Column(db.String(255),nullable=False); destination=db.Column(db.String(255),nullable=False); pickup_lat=db.Column(db.Float); pickup_lng=db.Column(db.Float); destination_lat=db.Column(db.Float); destination_lng=db.Column(db.Float); rider_fare=db.Column(db.Float,nullable=False); accepted_fare=db.Column(db.Float); shared=db.Column(db.Boolean,default=False,nullable=False); status=db.Column(db.String(30),default='requested',nullable=False); created_at=db.Column(db.DateTime,default=datetime.utcnow); offers=db.relationship('RideOffer',backref='ride',lazy=True,cascade='all, delete-orphan')
class RideOffer(db.Model):
 id=db.Column(db.Integer,primary_key=True); ride_id=db.Column(db.Integer,db.ForeignKey('ride.id'),nullable=False); driver_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); amount=db.Column(db.Float,nullable=False); status=db.Column(db.String(20),default='pending',nullable=False); distance_km=db.Column(db.Float); created_at=db.Column(db.DateTime,default=datetime.utcnow)
class Payment(db.Model):
 id=db.Column(db.Integer,primary_key=True); ride_id=db.Column(db.Integer,db.ForeignKey('ride.id'),unique=True,nullable=False); amount=db.Column(db.Float,nullable=False); method=db.Column(db.String(30),default='cash',nullable=False); status=db.Column(db.String(20),default='pending',nullable=False); reference=db.Column(db.String(100),unique=True); created_at=db.Column(db.DateTime,default=datetime.utcnow)
class Rating(db.Model):
 id=db.Column(db.Integer,primary_key=True); ride_id=db.Column(db.Integer,db.ForeignKey('ride.id'),nullable=False); from_user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); to_user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False); score=db.Column(db.Integer,nullable=False); comment=db.Column(db.String(500)); created_at=db.Column(db.DateTime,default=datetime.utcnow)
@login_manager.user_loader
def load_user(uid): return db.session.get(User,int(uid))
def create_app():
 app=Flask(__name__,template_folder='templates',static_folder='static'); app.config['SECRET_KEY']=os.environ.get('SECRET_KEY','dev-change-this-secret'); app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///'+os.path.join(BASE_DIR,'mymolue.db'); app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False; db.init_app(app); bcrypt.init_app(app); login_manager.init_app(app)
 with app.app_context(): db.create_all()
 return app
app=create_app()
def role_required(role):
 def deco(fn):
  @wraps(fn)
  @login_required
  def wrapped(*a,**kw):
   if current_user.role!=role: return jsonify(error=f'Only {role}s can perform this action'),403
   return fn(*a,**kw)
  return wrapped
 return deco
@app.route('/')
def index(): return render_template('index.html')
@app.route('/register',methods=['GET','POST'])
def register():
 if request.method=='POST':
  f=request.form; name=f.get('name','').strip(); email=f.get('email','').strip().lower(); phone=f.get('phone','').strip(); password=f.get('password',''); role=f.get('role','rider') if f.get('role') in {'rider','driver'} else 'rider'
  if not all([name,email,phone,password]) or len(password)<6: flash('Complete every field and use a password of at least 6 characters.','error'); return render_template('register.html')
  if User.query.filter((User.email==email)|(User.phone==phone)).first(): flash('An account with that email or phone already exists.','error'); return render_template('register.html')
  u=User(name=name,email=email,phone=phone,role=role,password_hash=bcrypt.generate_password_hash(password).decode()); db.session.add(u); db.session.commit(); login_user(u); return redirect(url_for('dashboard'))
 return render_template('register.html')
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=User.query.filter_by(email=request.form.get('email','').strip().lower()).first()
  if u and bcrypt.check_password_hash(u.password_hash,request.form.get('password','')): login_user(u); return redirect(url_for('dashboard'))
  flash('Invalid email or password.','error')
 return render_template('login.html')
@app.route('/logout')
@login_required
def logout(): current_user.is_online=False; db.session.commit(); logout_user(); return redirect(url_for('index'))
@app.route('/dashboard')
@login_required
def dashboard():
 rides=Ride.query.filter((Ride.rider_id==current_user.id)|(Ride.driver_id==current_user.id)).order_by(Ride.created_at.desc()).all(); return render_template('dashboard.html',rides=rides)
@app.route('/driver/availability',methods=['POST'])
@role_required('driver')
def availability(): current_user.is_online=request.form.get('online')=='true'; db.session.commit(); return jsonify(online=current_user.is_online)
@app.route('/location',methods=['POST'])
@login_required
def location():
 try: lat=float(request.form.get('latitude')); lng=float(request.form.get('longitude'))
 except (TypeError,ValueError): return jsonify(error='valid coordinates required'),400
 if not -90<=lat<=90 or not -180<=lng<=180: return jsonify(error='coordinates out of range'),400
 current_user.latitude=lat; current_user.longitude=lng; db.session.commit(); return jsonify(latitude=lat,longitude=lng)
@app.route('/nearby-drivers')
@login_required
def nearby_drivers():
 if current_user.latitude is None or current_user.longitude is None: return jsonify(error='location unavailable'),400
 out=[]
 for d in User.query.filter_by(role='driver',is_online=True).all():
  if d.latitude is not None and d.longitude is not None: out.append({'id':d.id,'name':d.name,'distance_km':round(haversine_km(current_user.latitude,current_user.longitude,d.latitude,d.longitude),2)})
 return jsonify(sorted(out,key=lambda x:x['distance_km']))
@app.route('/request-ride',methods=['POST'])
@role_required('rider')
def request_ride():
 f=request.form
 try: fare=float(f.get('fare','0')); plat=float(f.get('pickup_lat')); plng=float(f.get('pickup_lng')); dlat=float(f.get('destination_lat')); dlng=float(f.get('destination_lng'))
 except (TypeError,ValueError): fare=0; plat=plng=dlat=dlng=None
 if not f.get('pickup','').strip() or not f.get('destination','').strip() or fare<=0: flash('Enter valid trip details.','error'); return redirect(url_for('dashboard'))
 r=Ride(rider_id=current_user.id,pickup=f['pickup'].strip(),destination=f['destination'].strip(),pickup_lat=plat,pickup_lng=plng,destination_lat=dlat,destination_lng=dlng,rider_fare=fare,shared=f.get('shared')=='on'); db.session.add(r); db.session.commit(); flash('Ride requested.','success'); return redirect(url_for('dashboard'))
@app.route('/rides')
@role_required('driver')
def rides():
 out=[]
 for r in Ride.query.filter_by(status='requested').all():
  dist=None
  if current_user.latitude is not None and current_user.longitude is not None and r.pickup_lat is not None and r.pickup_lng is not None: dist=round(haversine_km(current_user.latitude,current_user.longitude,r.pickup_lat,r.pickup_lng),2)
  out.append({'id':r.id,'pickup':r.pickup,'destination':r.destination,'fare':r.rider_fare,'shared':r.shared,'offers':len(r.offers),'distance_km':dist})
 return jsonify(out)
@app.route('/ride/<int:ride_id>/offer',methods=['POST'])
@role_required('driver')
def offer(ride_id):
 r=db.get_or_404(Ride,ride_id)
 if r.status!='requested' or not current_user.is_online: return jsonify(error='ride unavailable or driver offline'),400
 try: amount=float(request.form.get('offer','0'))
 except ValueError: amount=0
 if amount<=0: return jsonify(error='invalid offer'),400
 dist=None
 if current_user.latitude is not None and current_user.longitude is not None and r.pickup_lat is not None and r.pickup_lng is not None: dist=round(haversine_km(current_user.latitude,current_user.longitude,r.pickup_lat,r.pickup_lng),2)
 o=RideOffer.query.filter_by(ride_id=ride_id,driver_id=current_user.id).first()
 if o: o.amount=amount; o.status='pending'; o.distance_km=dist
 else: db.session.add(RideOffer(ride_id=ride_id,driver_id=current_user.id,amount=amount,distance_km=dist))
 db.session.commit(); flash('Offer sent.','success'); return redirect(url_for('dashboard'))
@app.route('/ride/<int:ride_id>/offers')
@login_required
def offers(ride_id):
 r=db.get_or_404(Ride,ride_id)
 if r.rider_id!=current_user.id: return jsonify(error='unauthorized'),403
 return jsonify([{'id':o.id,'driver':o.driver.name,'amount':o.amount,'distance_km':o.distance_km,'status':o.status} for o in r.offers])
@app.route('/ride/<int:ride_id>/accept/<int:offer_id>',methods=['POST'])
@role_required('rider')
def accept(ride_id,offer_id):
 r=db.get_or_404(Ride,ride_id); o=db.get_or_404(RideOffer,offer_id)
 if r.rider_id!=current_user.id or o.ride_id!=ride_id or r.status!='requested': return jsonify(error='offer cannot be accepted'),400
 r.driver_id=o.driver_id; r.accepted_fare=o.amount; r.status='accepted'; o.status='accepted'
 for x in r.offers:
  if x.id!=o.id: x.status='rejected'
 db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/ride/<int:ride_id>/status',methods=['POST'])
@login_required
def status(ride_id):
 r=db.get_or_404(Ride,ride_id); new=request.form.get('status','')
 if current_user.id not in {r.rider_id,r.driver_id}: return jsonify(error='unauthorized'),403
 transitions={'accepted':{'arriving','cancelled'},'arriving':{'in_progress','cancelled'},'in_progress':{'completed','cancelled'},'requested':{'cancelled'}}
 if new not in transitions.get(r.status,set()): return jsonify(error='invalid transition',current=r.status),400
 if new in {'arriving','in_progress','completed'} and current_user.id!=r.driver_id: return jsonify(error='driver only'),403
 r.status=new
 if new in {'completed','cancelled'} and r.driver_id: r.driver.is_online=True
 db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/ride/<int:ride_id>/payment',methods=['POST'])
@login_required
def payment(ride_id):
 r=db.get_or_404(Ride,ride_id)
 if current_user.id not in {r.rider_id,r.driver_id} or r.status!='completed': return jsonify(error='payment unavailable'),400
 method=request.form.get('method','cash'); p=Payment.query.filter_by(ride_id=ride_id).first()
 if not p:
  p=Payment(ride_id=ride_id,amount=r.accepted_fare or r.rider_fare,method=method,status='paid' if method=='cash' else 'pending',reference=f'MM-{ride_id}-{int(datetime.utcnow().timestamp())}'); db.session.add(p)
 db.session.commit(); return jsonify(payment_id=p.id,status=p.status,method=p.method,amount=p.amount,reference=p.reference)
@app.route('/ride/<int:ride_id>/rate',methods=['POST'])
@login_required
def rate(ride_id):
 r=db.get_or_404(Ride,ride_id)
 if r.status!='completed' or current_user.id not in {r.rider_id,r.driver_id}: return jsonify(error='rating unavailable'),400
 to_id=r.driver_id if current_user.id==r.rider_id else r.rider_id
 try: score=int(request.form.get('score'))
 except (TypeError,ValueError): return jsonify(error='invalid score'),400
 if not 1<=score<=5: return jsonify(error='score must be 1-5'),400
 if Rating.query.filter_by(ride_id=ride_id,from_user_id=current_user.id).first(): return jsonify(error='already rated'),409
 db.session.add(Rating(ride_id=ride_id,from_user_id=current_user.id,to_user_id=to_id,score=score,comment=request.form.get('comment','')[:500])); db.session.commit(); return jsonify(success=True)
@app.route('/admin')
@login_required
def admin():
 if current_user.role!='admin': return jsonify(error='admin only'),403
 return jsonify(users=User.query.count(),drivers_online=User.query.filter_by(role='driver',is_online=True).count(),rides=Ride.query.count(),completed=Ride.query.filter_by(status='completed').count(),paid=Payment.query.filter_by(status='paid').count())
if __name__=='__main__': app.run(debug=True)
